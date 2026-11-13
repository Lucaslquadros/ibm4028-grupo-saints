"""Operações de banco. As rotas chamam daqui — elas não montam query.

Separar assim deixa a regra testável sem subir servidor HTTP e evita que
`routers/` vire um arquivão com SQL no meio.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Casa, LinhaCusto, MovimentoGrupo, UploadCusto, UploadFechamento
from app.schemas import CasaCreate, CasaUpdate
from app.services.leitor_fechamento import MovimentoLido, primeiros_meses_sem_estoque_inicial
from app.services.leitores import BASE_COMPRAS, BASE_CONSUMO, BASE_DECLARADA, Linha, base_do_total

JANELA_ACUMULADO = 12
"""Meses (terminando no período pedido) que entram no acumulado."""

MESES_MINIMOS_ACUMULADO = 6
"""Com o lado real só em compras, quantos meses somados bastam para a variação
de estoque virar ruído. Na casa piloto o estoque é menor que um mês de custo:
somando 6 meses, uma variação do tamanho do estoque inteiro pesa menos de 1/6
do custo. Na base real, jun–dez/22 oscilou de −7,2 a +9,3 pp mês a mês e fechou
em +0,5 pp somado.
"""


# ------------------------------------------------------------------ Casa
def listar_casas(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    ativa: bool | None = None,
    busca: str | None = None,
) -> tuple[int, list[Casa]]:
    """Devolve (total, página). O total é contado com os mesmos filtros."""
    stmt = select(Casa)

    if ativa is not None:
        stmt = stmt.where(Casa.ativa == ativa)
    if busca:
        stmt = stmt.where(Casa.nome.ilike(f"%{busca}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    casas = list(db.scalars(stmt.order_by(Casa.id).limit(limit).offset(offset)).all())
    return total, casas


def buscar_casa(db: Session, casa_id: int) -> Casa | None:
    """None quando não existe. Quem decide devolver 404 é a rota."""
    return db.get(Casa, casa_id)


def criar_casa(db: Session, dados: CasaCreate) -> Casa:
    casa = Casa(**dados.model_dump())
    db.add(casa)
    db.commit()
    db.refresh(casa)
    return casa


def atualizar_casa(db: Session, casa: Casa, dados: CasaUpdate) -> Casa:
    # exclude_unset: só o que o cliente realmente mandou. É o que faz o PATCH
    # ser PATCH — sem isso, campo omitido viraria None e apagaria dado.
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(casa, campo, valor)
    db.commit()
    db.refresh(casa)
    return casa


def remover_casa(db: Session, casa: Casa) -> None:
    db.delete(casa)
    db.commit()


# -------------------------------------------------------- Upload de custo (RF01)
def buscar_upload_existente(
    db: Session, *, casa_id: int, periodo: str, tipo: str
) -> UploadCusto | None:
    return db.scalar(
        select(UploadCusto).where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.periodo == periodo,
            UploadCusto.tipo == tipo,
        )
    )


def registrar_upload_custo(
    db: Session,
    *,
    casa_id: int,
    periodo: str,
    tipo: str,
    nome_original: str,
    blob_name: str,
    content_type: str,
    tamanho_bytes: int,
    url: str,
    linhas: list[Linha],
) -> UploadCusto:
    """Grava o upload e as linhas extraídas. Se já havia um upload da mesma
    casa/período/tipo, ele é substituído (reenviar o export corrige o mês).
    Quem apaga o blob antigo é a rota, depois do commit."""
    antigo = buscar_upload_existente(db, casa_id=casa_id, periodo=periodo, tipo=tipo)
    if antigo is not None:
        db.delete(antigo)
        db.flush()

    upload = UploadCusto(
        casa_id=casa_id,
        periodo=periodo,
        tipo=tipo,
        nome_original=nome_original,
        blob_name=blob_name,
        content_type=content_type,
        tamanho_bytes=tamanho_bytes,
        url=url,
    )
    upload.linhas = [
        LinhaCusto(
            nivel=linha.nivel,
            grupo=linha.grupo,
            subgrupo=linha.subgrupo,
            nome=linha.nome[:200],
            quantidade=linha.quantidade,
            venda_liquida=linha.venda_liquida,
            custo=linha.custo,
        )
        for linha in linhas
    ]
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def contar_linhas(db: Session, upload_id: int) -> int:
    return (
        db.scalar(select(func.count(LinhaCusto.id)).where(LinhaCusto.upload_id == upload_id)) or 0
    )


def _filtros_upload(casa_id: int | None, periodo: str | None) -> list:
    filtros = []
    if casa_id is not None:
        filtros.append(UploadCusto.casa_id == casa_id)
    if periodo is not None:
        filtros.append(UploadCusto.periodo == periodo)
    return filtros


def stmt_listar_uploads_custo(
    *,
    limit: int = 50,
    offset: int = 0,
    casa_id: int | None = None,
    periodo: str | None = None,
):
    """A query da listagem, isolada para poder ser compilada num teste.

    A contagem de linhas é uma **subquery escalar correlacionada**, não um
    `GROUP BY`. Os dois somam no banco (nunca em Python), mas só a subquery
    funciona nos dois bancos que este projeto usa:

      - A versão com `select(UploadCusto, count(...)).group_by(UploadCusto.id)`
        roda no SQLite, que tolera coluna "solta" no SELECT sob GROUP BY.
      - O Azure SQL **recusa** a mesma query ("column is invalid in the select
        list because it is not contained in either an aggregate function or the
        GROUP BY clause"), porque `select(UploadCusto)` expande para todas as
        colunas da tabela e só `id` estava agrupado.

    Isso derrubou `GET /api/v1/uploads-custo` em produção com 500 enquanto a
    suíte seguia verde, porque os testes rodam em SQLite. Ver
    `test_listar_uploads_e_compativel_com_sql_server`.
    """
    linhas = (
        select(func.count(LinhaCusto.id))
        .where(LinhaCusto.upload_id == UploadCusto.id)
        .scalar_subquery()
    )
    return (
        select(UploadCusto, linhas)
        .where(*_filtros_upload(casa_id, periodo))
        # ORDER BY não é cosmético aqui: o SQL Server exige um para paginar.
        .order_by(UploadCusto.periodo.desc(), UploadCusto.id.desc())
        .limit(limit)
        .offset(offset)
    )


def listar_uploads_custo(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    casa_id: int | None = None,
    periodo: str | None = None,
) -> tuple[int, list[tuple[UploadCusto, int]]]:
    """Devolve (total, [(upload, nº de linhas)])."""
    filtros = _filtros_upload(casa_id, periodo)
    total = db.scalar(select(func.count(UploadCusto.id)).where(*filtros)) or 0
    stmt = stmt_listar_uploads_custo(limit=limit, offset=offset, casa_id=casa_id, periodo=periodo)
    return total, [(upload, n) for upload, n in db.execute(stmt).all()]


# ------------------------------------- Upload da planilha-modelo de fechamento
def meses_sem_estoque_inicial(
    db: Session, casa_id: int, movimentos: list[MovimentoLido]
) -> list[MovimentoLido]:
    """Os movimentos sem `estoque_inicial` que não têm de onde tirá-lo.

    O estoque de abertura de um mês em branco é o `estoque_final` do mês
    anterior: no próprio arquivo ou num envio anterior. Envio anterior só vale
    se o mês anterior **não** está no arquivo — se está, o arquivo substitui o
    mês inteiro, e o grupo que faltar nele some do banco.
    """
    candidatos = primeiros_meses_sem_estoque_inicial(movimentos)
    if not candidatos:
        return []
    meses_no_arquivo = {m.periodo for m in movimentos}
    anteriores = {_periodo_menos(m.periodo, 1) for m in candidatos} - meses_no_arquivo
    no_banco = (
        set(
            db.execute(
                select(MovimentoGrupo.periodo, MovimentoGrupo.grupo).where(
                    MovimentoGrupo.casa_id == casa_id,
                    MovimentoGrupo.periodo.in_(anteriores),
                )
            )
            .tuples()
            .all()
        )
        if anteriores
        else set()
    )
    return [m for m in candidatos if (_periodo_menos(m.periodo, 1), m.grupo) not in no_banco]


def registrar_upload_fechamento(
    db: Session,
    *,
    casa_id: int,
    nome_original: str,
    blob_name: str,
    content_type: str,
    tamanho_bytes: int,
    url: str,
    movimentos: list[MovimentoLido],
) -> tuple[UploadFechamento, list[str], list[str]]:
    """Grava o envio e devolve (upload, meses substituídos, blobs a apagar).

    Cada mês do arquivo substitui o mês **inteiro** no banco — todos os grupos,
    não só os que vieram. É a mesma regra do reenvio do caminho antigo, e é a
    que o usuário espera: "mandei setembro de novo" quer dizer "esqueça o
    setembro anterior". Envio anterior que fica sem nenhum mês é apagado;
    quem apaga o blob dele é a rota, depois do commit.
    """
    meses = sorted({m.periodo for m in movimentos})
    substituidos = sorted(
        db.scalars(
            select(MovimentoGrupo.periodo)
            .where(MovimentoGrupo.casa_id == casa_id, MovimentoGrupo.periodo.in_(meses))
            .distinct()
        ).all()
    )
    db.execute(
        delete(MovimentoGrupo).where(
            MovimentoGrupo.casa_id == casa_id, MovimentoGrupo.periodo.in_(meses)
        )
    )

    upload = UploadFechamento(
        casa_id=casa_id,
        nome_original=nome_original,
        blob_name=blob_name,
        content_type=content_type,
        tamanho_bytes=tamanho_bytes,
        url=url,
    )
    upload.movimentos = [
        MovimentoGrupo(
            casa_id=casa_id,
            periodo=m.periodo,
            grupo=m.grupo,
            venda_liquida=m.venda_liquida,
            custo_teorico=m.custo_teorico,
            estoque_inicial=m.estoque_inicial,
            compras=m.compras,
            estoque_final=m.estoque_final,
        )
        for m in movimentos
    ]
    db.add(upload)
    db.flush()

    vazios = list(
        db.scalars(
            select(UploadFechamento).where(
                UploadFechamento.casa_id == casa_id,
                UploadFechamento.id != upload.id,
                ~select(MovimentoGrupo.id)
                .where(MovimentoGrupo.upload_id == UploadFechamento.id)
                .exists(),
            )
        ).all()
    )
    blobs_orfaos = [u.blob_name for u in vazios]
    for antigo in vazios:
        db.delete(antigo)

    db.commit()
    db.refresh(upload)
    return upload, substituidos, blobs_orfaos


def stmt_periodos_por_upload_fechamento(upload_ids: list[int]):
    """[(upload_id, periodo, nº de grupos)] — statement isolado para ser
    compilado no dialeto do SQL Server (`tests/test_dialeto_sql.py`)."""
    return (
        select(MovimentoGrupo.upload_id, MovimentoGrupo.periodo, func.count(MovimentoGrupo.id))
        .where(MovimentoGrupo.upload_id.in_(upload_ids))
        .group_by(MovimentoGrupo.upload_id, MovimentoGrupo.periodo)
        .order_by(MovimentoGrupo.upload_id, MovimentoGrupo.periodo)
    )


def listar_uploads_fechamento(
    db: Session, *, casa_id: int | None = None, limit: int = 50, offset: int = 0
) -> tuple[int, list[tuple[UploadFechamento, list[str], int]]]:
    """Devolve (total, [(upload, meses, nº de linhas)]), do mais recente ao mais antigo."""
    filtros = [UploadFechamento.casa_id == casa_id] if casa_id is not None else []
    total = db.scalar(select(func.count(UploadFechamento.id)).where(*filtros)) or 0
    uploads = list(
        db.scalars(
            select(UploadFechamento)
            .where(*filtros)
            .order_by(UploadFechamento.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    if not uploads:
        return total, []

    meses: dict[int, list[str]] = {u.id: [] for u in uploads}
    linhas: dict[int, int] = dict.fromkeys(meses, 0)
    for upload_id, periodo, n in db.execute(stmt_periodos_por_upload_fechamento(list(meses))).all():
        meses[upload_id].append(periodo)
        linhas[upload_id] += n
    return total, [(u, meses[u.id], linhas[u.id]) for u in uploads]


# --------------------------------------------------------- Fechamento de CMV
def grupos_comparaveis(db: Session, casa_id: int) -> list[str]:
    """Os grupos que formam o CMV direto desta casa — **deduzidos do dado**.

    Antes isto era uma constante `("ALIMENTOS", "BEBIDAS")`. Funcionava para o
    Grupo Saints e falsificava a tese de que o sistema serve a outro negócio:
    categoria de restaurante cravada no código não vale para uma farmácia.

    A regra que substitui a lista não precisa de configuração nenhuma: um grupo
    só é comparável se **os dois lados do fechamento o reportam**. É o que
    distingue custo de mercadoria de todo o resto:

      - só na DRE de compras: UTENSILIOS, MATERIAL DE CONSUMO, PRODUTOS REVENDA
        → custo indireto, sem baixa de estoque, não tem teórico para comparar
      - só na engenharia de cardápio: SERVICOS (couvert), OUTRAS VENDAS
        → receita sem custo de mercadoria, não tem real para comparar
      - nos dois: ALIMENTOS, BEBIDAS → o CMV direto

    Na base real do cliente a interseção devolve exatamente ALIMENTOS e BEBIDAS,
    ou seja, o mesmo resultado da lista antiga, sem cravar o domínio.

    O conjunto é por casa (não por mês) de propósito: 23 dos 24 meses de
    histórico têm só o cardápio, e exigir os dois relatórios no mesmo mês
    esvaziaria a série histórica. Os meses incompletos herdam o conjunto
    aprendido nos meses completos da mesma casa.
    """
    stmt = (
        select(LinhaCusto.grupo)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(UploadCusto.casa_id == casa_id, LinhaCusto.nivel == "grupo")
        .group_by(LinhaCusto.grupo)
        .having(func.count(func.distinct(UploadCusto.tipo)) >= 2)
    )
    grupos = sorted(db.scalars(stmt).all())
    if grupos:
        return grupos

    # Nenhum mês tem os dois relatórios: não há como deduzir comparabilidade.
    # Cai para os grupos que têm custo de mercadoria — sem o outro lado não há
    # ajuste a calcular, então isto afeta só o CMV teórico exibido.
    alternativa = (
        select(LinhaCusto.grupo)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(UploadCusto.casa_id == casa_id, LinhaCusto.nivel == "grupo")
        .group_by(LinhaCusto.grupo)
        .having(func.sum(LinhaCusto.custo) > 0)
    )
    return sorted(db.scalars(alternativa).all())


def _somas_por_grupo(
    db: Session, casa_id: int, grupos_cmv: list[str], periodos: list[str] | None = None
):
    """[(periodo, tipo, grupo, custo, venda)] somados no banco."""
    stmt = (
        select(
            UploadCusto.periodo,
            UploadCusto.tipo,
            LinhaCusto.grupo,
            func.sum(LinhaCusto.custo),
            func.sum(LinhaCusto.venda_liquida),
        )
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            LinhaCusto.nivel == "grupo",
            LinhaCusto.grupo.in_(grupos_cmv),
        )
        .group_by(UploadCusto.periodo, UploadCusto.tipo, LinhaCusto.grupo)
    )
    if periodos is not None:
        stmt = stmt.where(UploadCusto.periodo.in_(periodos))
    return db.execute(stmt).all()


def stmt_subgrupos_por_lado(*, casa_id: int, periodo: str, grupos: list[str]):
    """Os subgrupos do mês, por lado do fechamento — statement isolado.

    Separado da função para ser compilado no dialeto do SQL Server em
    `tests/test_dialeto_sql.py`. O `GROUP BY` aqui é seguro porque as três
    colunas não agregadas (`tipo`, `grupo`, `subgrupo`) estão todas agrupadas —
    foi exatamente isso que faltou na query que derrubou `/uploads-custo` com
    500 em produção enquanto a suíte em SQLite seguia verde.
    """
    return (
        select(
            UploadCusto.tipo,
            LinhaCusto.grupo,
            LinhaCusto.subgrupo,
            func.sum(LinhaCusto.custo),
            func.sum(LinhaCusto.venda_liquida),
        )
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.periodo == periodo,
            LinhaCusto.nivel == "subgrupo",
            LinhaCusto.subgrupo.is_not(None),
            LinhaCusto.grupo.in_(grupos),
        )
        .group_by(UploadCusto.tipo, LinhaCusto.grupo, LinhaCusto.subgrupo)
    )


def subgrupos_por_lado(
    db: Session, *, casa_id: int, periodo: str, grupos: list[str]
) -> list[tuple]:
    """[(tipo, grupo, subgrupo, custo, venda)] somados no banco (regra 6).

    Alimenta a comparação por subgrupo do RF11. Quem decide o que é par e o que
    é composição de custo é `app/services/explicacao.py` — aqui só se soma.
    """
    if not grupos:
        return []
    stmt = stmt_subgrupos_por_lado(casa_id=casa_id, periodo=periodo, grupos=grupos)
    return [
        (tipo, grupo, subgrupo, float(custo or 0), float(venda) if venda is not None else None)
        for tipo, grupo, subgrupo, custo, venda in db.execute(stmt).all()
    ]


def _totais_compras(db: Session, casa_id: int, periodos: list[str] | None = None):
    """{periodo: (receita líquida da DRE, base do lado real)}.

    A receita é o denominador quando o cardápio do mês ainda não foi enviado.
    A base (compras | consumo | declarada) vem do nome da linha total — ver
    `leitores.base_do_total`.
    """
    stmt = (
        select(UploadCusto.periodo, LinhaCusto.venda_liquida, LinhaCusto.nome)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.tipo == "compras",
            LinhaCusto.nivel == "total",
        )
    )
    if periodos is not None:
        stmt = stmt.where(UploadCusto.periodo.in_(periodos))
    return {
        periodo: (float(v) if v is not None else None, base_do_total(nome))
        for periodo, v, nome in db.execute(stmt).all()
    }


def _pct(custo: float | None, venda: float | None) -> float | None:
    if custo is None or not venda:
        return None
    return round(custo / venda * 100, 2)


def _montar_linha(
    grupo: str, custo_teorico: float | None, custo_real: float | None, venda: float | None
) -> dict:
    teorico_pct = _pct(custo_teorico, venda)
    real_pct = _pct(custo_real, venda)
    ajuste = (
        round(custo_real - custo_teorico, 2)
        if custo_real is not None and custo_teorico is not None
        else None
    )
    ajuste_pp = (
        round(real_pct - teorico_pct, 2)
        if real_pct is not None and teorico_pct is not None
        else None
    )
    return {
        "grupo": grupo,
        "venda_liquida": round(venda, 2) if venda is not None else None,
        "custo_teorico": round(custo_teorico, 2) if custo_teorico is not None else None,
        "custo_real": round(custo_real, 2) if custo_real is not None else None,
        "cmv_teorico_pct": teorico_pct,
        "cmv_real_pct": real_pct,
        "ajuste": ajuste,
        "ajuste_pp": ajuste_pp,
    }


def _fechamentos(db: Session, casa_id: int, periodos: list[str] | None = None) -> dict:
    """{periodo: {"tem_cardapio", "tem_compras", "grupos": [...], "total": {...}}}

    Regra do cálculo (ver docs/07-fechamento-cmv.md):
      teórico = custo do grupo no cardápio (vendas × ficha técnica)
      real    = custo do grupo no lado real. Depende da `base_real`:
                consumo   → EI + compras − EF: é o CMV real
                compras   → só as compras do mês (DRE do Everest): falta o
                            estoque, e o mês isolado NÃO é conclusivo
                declarada → planilha genérica com `custo`, sem como conferir
      CMV %   = custo ÷ venda líquida do grupo no cardápio — o MESMO
                denominador nos dois lados, para que a diferença em pontos
                percentuais seja só diferença de custo. Sem cardápio no mês,
                usa a receita líquida da DRE.
      ajuste  = real − teórico

    Casa que já recebeu a planilha-modelo é calculada só por ela
    (`_fechamentos_movimento`): misturar os dois caminhos na mesma casa poria
    compras de um mês ao lado de consumo de outro na mesma série.
    """
    if usa_planilha_fechamento(db, casa_id):
        return _fechamentos_movimento(db, casa_id, periodos)

    grupos_cmv = grupos_comparaveis(db, casa_id)
    if not grupos_cmv:
        return {}

    somas: dict[str, dict] = {}
    for periodo, tipo, grupo, custo, venda in _somas_por_grupo(db, casa_id, grupos_cmv, periodos):
        mes = somas.setdefault(periodo, {})
        g = mes.setdefault(grupo, {"cardapio": None, "compras": None, "venda": None})
        g[tipo] = float(custo) if custo is not None else None
        if tipo == "cardapio" and venda is not None:
            g["venda"] = float(venda)

    totais_compras = _totais_compras(db, casa_id, periodos)
    resultado = {}
    for periodo, grupos in somas.items():
        tem_cardapio = any(g["cardapio"] is not None for g in grupos.values())
        tem_compras = any(g["compras"] is not None for g in grupos.values())
        linhas = []
        tot_teorico = tot_real = tot_venda = None
        for nome in grupos_cmv:
            g = grupos.get(nome)
            if g is None:
                continue
            venda = g["venda"]
            linhas.append(_montar_linha(nome, g["cardapio"], g["compras"], venda))
            if g["cardapio"] is not None:
                tot_teorico = (tot_teorico or 0) + g["cardapio"]
            if g["compras"] is not None:
                tot_real = (tot_real or 0) + g["compras"]
            if venda is not None:
                tot_venda = (tot_venda or 0) + venda

        if not tem_cardapio:
            # sem venda por grupo: CMV % só no total, sobre a receita da DRE
            tot_venda = totais_compras.get(periodo, (None, None))[0]
            for linha in linhas:
                linha["cmv_real_pct"] = None

        resultado[periodo] = {
            "tem_cardapio": tem_cardapio,
            "tem_compras": tem_compras,
            "grupos": linhas,
            "total": _montar_linha("TOTAL", tot_teorico, tot_real, tot_venda),
            "base_real": totais_compras.get(periodo, (None, None))[1] if tem_compras else None,
            # Vai junto para a rota do RF11 não precisar refazer a dedução de
            # `grupos_comparaveis` numa segunda consulta ao banco.
            "grupos_cmv": grupos_cmv,
        }
    return resultado


def usa_planilha_fechamento(db: Session, casa_id: int) -> bool:
    """A casa já recebeu a planilha-modelo de fechamento?"""
    return (
        db.scalar(select(MovimentoGrupo.id).where(MovimentoGrupo.casa_id == casa_id).limit(1))
        is not None
    )


def _coluna_periodo(db: Session, casa_id: int):
    """De onde vêm os meses da casa: da planilha-modelo, se ela já foi enviada,
    senão dos uploads do Everest. Mesma regra de `_fechamentos`."""
    if usa_planilha_fechamento(db, casa_id):
        return MovimentoGrupo.periodo
    return UploadCusto.periodo


def _filtro_casa(coluna, casa_id: int):
    tabela = MovimentoGrupo if coluna is MovimentoGrupo.periodo else UploadCusto
    return tabela.casa_id == casa_id


def _soma_completa(valores: list[float | None]) -> float | None:
    """Soma só quando nenhum grupo ficou sem valor. Somar os que têm daria um
    total teórico de um grupo contra um total real de dois — ajuste falso."""
    if not valores or any(v is None for v in valores):
        return None
    return sum(valores)


def _fechamentos_movimento(db: Session, casa_id: int, periodos: list[str] | None) -> dict:
    """Mesmo formato de `_fechamentos`, a partir da planilha-modelo.

      teórico  = custo_teorico informado (nulo se a coluna veio vazia)
      real     = EI + compras − EF, com EI vazio = EF do mês anterior. É o CMV
                 real, por isso `base_real` é sempre "consumo"
      CMV %    = custo ÷ venda_liquida do grupo, igual nos dois lados

    Os grupos são os que o usuário pôs na planilha: ele já declara o que é
    custo direto, então não há o que deduzir (`grupos_comparaveis` não entra).
    """
    stmt = select(MovimentoGrupo).where(MovimentoGrupo.casa_id == casa_id)
    if periodos is not None:
        alvo = set(periodos) | {_periodo_menos(p, 1) for p in periodos}
        stmt = stmt.where(MovimentoGrupo.periodo.in_(alvo))
    movimentos = list(db.scalars(stmt).all())

    estoque_final = {(m.periodo, m.grupo): float(m.estoque_final) for m in movimentos}
    por_mes: dict[str, list[MovimentoGrupo]] = {}
    for m in movimentos:
        if periodos is None or m.periodo in periodos:
            por_mes.setdefault(m.periodo, []).append(m)

    resultado = {}
    for periodo, lista in por_mes.items():
        linhas, teoricos, reais, vendas = [], [], [], []
        for m in sorted(lista, key=lambda x: x.grupo):
            ei = (
                float(m.estoque_inicial)
                if m.estoque_inicial is not None
                else estoque_final.get((_periodo_menos(periodo, 1), m.grupo))
            )
            # EI irresolúvel só acontece se o mês anterior foi substituído sem
            # este grupo depois do envio: o grupo fica sem real, sem inventar.
            real = (
                round(ei + float(m.compras) - float(m.estoque_final), 2) if ei is not None else None
            )
            teorico = float(m.custo_teorico) if m.custo_teorico is not None else None
            venda = float(m.venda_liquida)
            linhas.append(_montar_linha(m.grupo, teorico, real, venda))
            teoricos.append(teorico)
            reais.append(real)
            vendas.append(venda)

        resultado[periodo] = {
            "tem_cardapio": any(t is not None for t in teoricos),
            "tem_compras": any(r is not None for r in reais),
            "grupos": linhas,
            "total": _montar_linha(
                "TOTAL", _soma_completa(teoricos), _soma_completa(reais), sum(vendas)
            ),
            "base_real": BASE_CONSUMO,
            "grupos_cmv": [linha["grupo"] for linha in linhas],
            # Sem subgrupo na planilha-modelo: a rota do RF11 não busca
            # subgrupos de uploads antigos do Everest para esta casa.
            "fonte": "planilha",
        }
    return resultado


def _periodo_menos(periodo: str, meses: int) -> str:
    """('2026-09', 11) → '2025-10'."""
    ano, mes = (int(x) for x in periodo.split("-"))
    indice = ano * 12 + (mes - 1) - meses
    return f"{indice // 12:04d}-{indice % 12 + 1:02d}"


def fechamento_acumulado(db: Session, casa_id: int, periodo: str) -> dict | None:
    """Teórico × real somados nos meses com os dois lados, até `periodo`.

    É a leitura que faz sentido quando o lado real é só compras: num mês, a
    diferença mistura desvio com o ritmo de compra e estoque; somando meses, a
    variação de estoque se dilui e sobra o desvio. Mesmo com consumo (EI − EF
    informado), o acumulado mostra se o mês é tendência ou ponto fora.

    Soma só grupos com os dois lados no mesmo mês — senão um lado entra sem o
    outro e o acumulado deixa de ser comparável. None quando nenhum mês da
    janela tem os dois relatórios.
    """
    inicio = _periodo_menos(periodo, JANELA_ACUMULADO - 1)
    coluna = _coluna_periodo(db, casa_id)
    periodos = list(
        db.scalars(
            select(coluna)
            .where(_filtro_casa(coluna, casa_id), coluna >= inicio, coluna <= periodo)
            .distinct()
        ).all()
    )
    fechamentos = _fechamentos(db, casa_id, periodos) if periodos else {}
    completos = sorted(p for p, f in fechamentos.items() if f["tem_cardapio"] and f["tem_compras"])
    if not completos:
        return None

    somas: dict[str, list[float]] = {}
    for p in completos:
        for linha in fechamentos[p]["grupos"]:
            if linha["custo_teorico"] is None or linha["custo_real"] is None:
                continue
            if not linha["venda_liquida"]:
                continue
            soma = somas.setdefault(linha["grupo"], [0.0, 0.0, 0.0])
            soma[0] += linha["custo_teorico"]
            soma[1] += linha["custo_real"]
            soma[2] += linha["venda_liquida"]

    grupos = [_montar_linha(g, t, r, v) for g, (t, r, v) in sorted(somas.items())]
    total = _montar_linha(
        "TOTAL",
        sum(s[0] for s in somas.values()),
        sum(s[1] for s in somas.values()),
        sum(s[2] for s in somas.values()),
    )
    bases = {fechamentos[p]["base_real"] for p in completos}
    base = next(
        (b for b in (BASE_COMPRAS, BASE_DECLARADA, BASE_CONSUMO) if b in bases), BASE_DECLARADA
    )
    mensais = [
        fechamentos[p]["total"]["ajuste_pp"]
        for p in completos
        if fechamentos[p]["total"]["ajuste_pp"] is not None
    ]
    return {
        "periodo_inicio": completos[0],
        "periodo_fim": completos[-1],
        "meses": len(completos),
        "periodos": completos,
        "base_real": base,
        "conclusivo": base != BASE_COMPRAS or len(completos) >= MESES_MINIMOS_ACUMULADO,
        "meses_minimos": MESES_MINIMOS_ACUMULADO,
        "ajuste_mensal_min_pp": min(mensais) if mensais else None,
        "ajuste_mensal_max_pp": max(mensais) if mensais else None,
        "total": total,
        "grupos": grupos,
    }


def calcular_fechamento(db: Session, casa_id: int, periodo: str) -> dict | None:
    """None quando não há nenhum upload da casa no período — a rota decide o 404."""
    return _fechamentos(db, casa_id, [periodo]).get(periodo)


def evolucao_cmv(db: Session, casa_id: int, limit: int = 24) -> list[dict]:
    """Os últimos `limit` meses com dado, em ordem cronológica."""
    coluna = _coluna_periodo(db, casa_id)
    periodos = list(
        db.scalars(
            select(coluna)
            .where(_filtro_casa(coluna, casa_id))
            .distinct()
            .order_by(coluna.desc())
            .limit(limit)
        ).all()
    )
    if not periodos:
        return []
    fechamentos = _fechamentos(db, casa_id, periodos)
    return [
        {
            "periodo": periodo,
            "cmv_teorico_pct": fechamentos[periodo]["total"]["cmv_teorico_pct"],
            "cmv_real_pct": fechamentos[periodo]["total"]["cmv_real_pct"],
            "ajuste_pp": fechamentos[periodo]["total"]["ajuste_pp"],
            "base_real": fechamentos[periodo]["base_real"],
        }
        for periodo in sorted(periodos)
        if periodo in fechamentos
    ]


def stmt_nomes_mais_custosos(*, casa_id: int, periodo: str, limit: int):
    """Os `limit` itens com maior custo acumulado até `periodo`, inclusive.

    Separado em statement próprio para ser compilado no dialeto do SQL Server
    pelo teste de `tests/test_dialeto_sql.py` — o `GROUP BY` aqui é seguro
    porque só `nome` é selecionado, e `ORDER BY` sobre agregação é permitido.
    """
    return (
        select(LinhaCusto.nome)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.tipo == "cardapio",
            LinhaCusto.nivel == "item",
            UploadCusto.periodo <= periodo,
        )
        .group_by(LinhaCusto.nome)
        .order_by(func.sum(LinhaCusto.custo).desc())
        .limit(limit)
    )


def historico_itens(
    db: Session, *, casa_id: int, periodo: str, limit_itens: int = 10
) -> list[tuple]:
    """[(nome, grupo, subgrupo, periodo, quantidade, custo)] dos itens que mais
    pesam no custo, mês a mês, até `periodo`.

    Alimenta a previsão de demanda do RF07. Duas consultas em vez de uma:
    primeiro quais itens interessam (os mais custosos), depois a série deles.
    Buscar a série de *todos* os itens para descartar 99% em Python seria
    trazer a tabela inteira para a aplicação — o que a regra 6 do projeto
    proíbe, e com razão: a casa piloto tem 345 itens por mês × 24 meses.

    A soma é por (item, mês) porque o mesmo nome pode aparecer em mais de uma
    linha do relatório (subgrupos diferentes para o mesmo produto).
    """
    nomes = list(
        db.scalars(
            stmt_nomes_mais_custosos(casa_id=casa_id, periodo=periodo, limit=limit_itens)
        ).all()
    )
    if not nomes:
        return []

    stmt = (
        select(
            LinhaCusto.nome,
            LinhaCusto.grupo,
            LinhaCusto.subgrupo,
            UploadCusto.periodo,
            func.sum(LinhaCusto.quantidade),
            func.sum(LinhaCusto.custo),
        )
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.tipo == "cardapio",
            LinhaCusto.nivel == "item",
            UploadCusto.periodo <= periodo,
            LinhaCusto.nome.in_(nomes),
        )
        .group_by(LinhaCusto.nome, LinhaCusto.grupo, LinhaCusto.subgrupo, UploadCusto.periodo)
        .order_by(LinhaCusto.nome, UploadCusto.periodo)
    )
    # Preserva a ordem de relevância (custo) que a primeira consulta definiu —
    # o ORDER BY acima é por nome, que é o que agrupa a série de cada item.
    relevancia = {nome: i for i, nome in enumerate(nomes)}
    linhas = db.execute(stmt).all()
    return sorted(linhas, key=lambda linha: (relevancia.get(linha[0], 999), linha[3]))


def top_itens_cardapio(
    db: Session,
    *,
    casa_id: int,
    periodo: str,
    ordem: str = "custo",
    limit: int = 10,
    venda_minima: float = 500.0,
) -> list[LinhaCusto]:
    """Itens do cardápio que mais pesam no CMV teórico.

    ordem="custo": maior custo total (onde está o dinheiro)
    ordem="cmv":   maior custo ÷ venda (prato com margem ruim); ignora itens
                   com venda abaixo de `venda_minima`, que distorcem o %.
    """
    stmt = (
        select(LinhaCusto)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.periodo == periodo,
            UploadCusto.tipo == "cardapio",
            LinhaCusto.nivel == "item",
        )
    )
    if ordem == "cmv":
        stmt = stmt.where(LinhaCusto.venda_liquida >= venda_minima).order_by(
            (LinhaCusto.custo / LinhaCusto.venda_liquida).desc()
        )
    else:
        stmt = stmt.order_by(LinhaCusto.custo.desc())
    return list(db.scalars(stmt.limit(limit)).all())
