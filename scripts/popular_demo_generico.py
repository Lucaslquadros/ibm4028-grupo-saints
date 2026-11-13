"""Carrega a unidade de demonstração de **outro segmento**, pela API.

    # local (API subida com `uv run fastapi dev app/main.py`)
    uv run python scripts/popular_demo_generico.py

    # produção
    uv run python scripts/popular_demo_generico.py \
        --api https://app-projeto4-saints2026.azurewebsites.net

    # só gerar as planilhas, para anexar numa apresentação ou enviar a alguém
    uv run python scripts/popular_demo_generico.py --apenas-planilhas pasta/

Para que serve
--------------
O sistema nasceu lendo dois relatórios do Everest de um grupo de bares. A
afirmação de que ele resolve o fechamento manual de **qualquer** negócio só vale
se existir dado de um negócio que não é esse. Este script cria esse dado:

  - uma unidade de outro segmento (farmácia), com 6 meses de histórico;
  - as duas pontas do fechamento em **planilha genérica**, não em export do
    Everest — exercitando `leitores.ler_planilha`;
  - um grupo (EMBALAGENS) que só existe no lado real, para mostrar
    `crud.grupos_comparaveis` excluindo custo indireto sem lista hardcoded.

Vai pela API de propósito (e não direto no banco, como
`scripts/importar_exports.py`): assim o `POST /api/v1/uploads-custo` é exercido
de verdade, com validação, Blob e tudo o que roda em produção.

Dado inventado, e rotulado como tal
-----------------------------------
Os números NÃO são do cliente. O nome da unidade carrega "(DEMO)" para que
ninguém confunda isto com a casa piloto real em nenhuma tela ou slide.
"""

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# O console do Windows abre em cp1252, que não tem "→" nem "ç": sem isto o
# script morre num UnicodeEncodeError no print, depois de já ter gravado o dado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from openpyxl import Workbook  # noqa: E402

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


TITULOS_TEORICO = ["grupo", "subgrupo", "item", "quantidade", "venda_liquida", "custo"]
TITULOS_REAL = ["grupo", "subgrupo", "item", "estoque_inicial", "compras", "estoque_final"]


def carregar_catalogo() -> tuple[list[str], list[dict]]:
    """Lê `exemplos/`: (meses, empresas). Nada de dado embutido no script.

    O dado fica em CSV versionado em vez de .xlsx porque o `.gitignore` bloqueia
    `*.xlsx` para planilha de cliente nunca entrar no Git — abrir exceção criaria
    um furo nessa proteção. O .xlsx é gerado aqui, na hora.

    Cada empresa tem dois CSVs, ambos com uma coluna `periodo`:

      - `<slug>-teorico.csv`: o relatório de vendas × ficha técnica de cada mês
        (grupo, subgrupo, item, quantidade, venda_liquida, custo).
      - `<slug>-real.csv`: o movimento de estoque de cada mês, a custo
        (grupo, subgrupo, item, estoque_inicial, compras, estoque_final).
        O custo real sai da regra do cliente, por item:
        **estoque inicial + compras − estoque final**.

    Os desvios entre os dois lados estão nos números, não num multiplicador:
    cada um tem causa nomeada em `exemplos/README.md`.
    """
    manifesto = json.loads((EXEMPLOS / "empresas.json").read_text(encoding="utf-8"))

    empresas, meses = [], set()
    for e in manifesto["empresas"]:
        teorico = _ler_csv(EXEMPLOS / f"{e['slug']}-teorico.csv", TITULOS_TEORICO)
        real = _ler_csv(EXEMPLOS / f"{e['slug']}-real.csv", TITULOS_REAL)
        _conferir_estoque(e["slug"], real)
        meses |= set(teorico) | set(real)
        empresas.append({**e, "teorico": teorico, "real": real})
    return sorted(meses), empresas


def _ler_csv(caminho: Path, esperados: list[str]) -> dict[str, list[dict]]:
    """{periodo: [linha como dict]}. Números viram float; o resto fica texto."""
    with caminho.open(encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        faltam = set(esperados + ["periodo"]) - set(leitor.fieldnames or [])
        if faltam:
            raise SystemExit(f"{caminho.name}: faltam as colunas {', '.join(sorted(faltam))}")
        por_mes: dict[str, list[dict]] = {}
        for linha in leitor:
            if not (linha.get("periodo") or "").strip():
                continue
            dados = {c: _talvez_numero(linha[c]) for c in esperados}
            por_mes.setdefault(linha["periodo"].strip(), []).append(dados)
    if not por_mes:
        raise SystemExit(f"{caminho.name} está vazio")
    return por_mes


def _talvez_numero(valor: str):
    try:
        return float(valor)
    except ValueError:
        return valor


def _conferir_estoque(slug: str, real: dict[str, list[dict]]) -> None:
    """O estoque inicial de um mês tem que ser o estoque final do mês anterior.

    É o que torna o "real" pós-inventário de verdade: se a contagem de um mês
    está errada, o erro aparece com sinal trocado no mês seguinte — e o
    fechamento mostra isso, em vez de esconder.
    """
    anterior: dict[tuple, float] = {}
    for periodo in sorted(real):
        for linha in real[periodo]:
            chave = (linha["grupo"], linha["subgrupo"], linha["item"])
            if chave in anterior and abs(anterior[chave] - linha["estoque_inicial"]) > 0.01:
                raise SystemExit(
                    f"{slug} {periodo} {linha['item']}: estoque inicial "
                    f"{linha['estoque_inicial']} ≠ estoque final do mês anterior {anterior[chave]}"
                )
            anterior[chave] = linha["estoque_final"]


def planilha_teorico(linhas: list[dict]) -> bytes:
    return _xlsx(TITULOS_TEORICO, [[linha[c] for c in TITULOS_TEORICO] for linha in linhas])


def planilha_real(linhas: list[dict]) -> bytes:
    """Movimento de estoque + a coluna `custo` = EI + compras − EF.

    As três colunas de estoque vão junto para quem abrir o arquivo conferir a
    conta; o leitor genérico ignora colunas que não conhece e usa só `custo`.
    """
    corpo = []
    for linha in linhas:
        custo = linha["estoque_inicial"] + linha["compras"] - linha["estoque_final"]
        corpo.append([linha[c] for c in TITULOS_REAL] + [round(custo, 2)])
    return _xlsx(TITULOS_REAL + ["custo"], corpo)


def _xlsx(titulos: list[str], linhas: list[list]) -> bytes:
    livro = Workbook()
    aba = livro.active
    aba.title = "Dados"
    aba.append(titulos)
    for linha in linhas:
        aba.append(linha)
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------ cliente HTTP
def _requisicao(url: str, dados: bytes | None, tipo: str | None, metodo: str) -> dict:
    req = urllib.request.Request(url, data=dados, method=metodo)
    if tipo:
        req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, timeout=120) as resposta:
            corpo = resposta.read().decode()
            return {"status": resposta.status, "corpo": corpo}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "corpo": exc.read().decode(errors="replace")}


def _multipart(campos: dict[str, str], nome_arquivo: str, conteudo: bytes) -> tuple[bytes, str]:
    """Monta o corpo multipart à mão para não precisar de `requests` só por isto."""
    limite = f"----demo{uuid.uuid4().hex}"
    partes = bytearray()
    for chave, valor in campos.items():
        partes += f"--{limite}\r\n".encode()
        partes += f'Content-Disposition: form-data; name="{chave}"\r\n\r\n'.encode()
        partes += f"{valor}\r\n".encode()
    partes += f"--{limite}\r\n".encode()
    partes += (
        f'Content-Disposition: form-data; name="arquivo"; filename="{nome_arquivo}"\r\n'
    ).encode()
    partes += f"Content-Type: {XLSX}\r\n\r\n".encode()
    partes += conteudo + b"\r\n"
    partes += f"--{limite}--\r\n".encode()
    return bytes(partes), f"multipart/form-data; boundary={limite}"


def garantir_casa(api: str, empresa: dict) -> int:
    """Devolve o id da unidade de demo, criando-a se ainda não existir.

    Idempotente de propósito: rodar duas vezes contra produção não duplica
    unidade, e reenviar um período substitui o upload anterior.
    """
    nome = empresa["nome"]
    busca = _requisicao(f"{api}/api/v1/casas?limit=200", None, None, "GET")
    if busca["status"] == 200:
        for casa in json.loads(busca["corpo"])["items"]:
            if casa["nome"] == nome:
                print(f"  unidade já existe: id {casa['id']}")
                return casa["id"]

    corpo = json.dumps(
        {"nome": nome, "marca": empresa["marca"], "cidade": empresa["cidade"], "ativa": True}
    ).encode()
    criada = _requisicao(f"{api}/api/v1/casas", corpo, "application/json", "POST")
    if criada["status"] != 201:
        raise SystemExit(f"Falhei ao criar a unidade ({criada['status']}): {criada['corpo']}")
    casa_id = json.loads(criada["corpo"])["id"]
    print(f"  unidade criada: id {casa_id}")
    return casa_id


def enviar(api: str, casa_id: int, periodo: str, tipo: str, conteudo: bytes) -> None:
    campos = {"casa_id": str(casa_id), "periodo": periodo, "tipo": tipo}
    corpo, content_type = _multipart(campos, f"{tipo}-{periodo}.xlsx", conteudo)
    resposta = _requisicao(f"{api}/api/v1/uploads-custo", corpo, content_type, "POST")
    if resposta["status"] != 201:
        raise SystemExit(f"{periodo} {tipo}: HTTP {resposta['status']} — {resposta['corpo']}")
    return json.loads(resposta["corpo"])["linhas_importadas"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    parser.add_argument(
        "--empresa",
        action="append",
        metavar="SLUG",
        help="Carrega só este slug (pode repetir). Sem a flag, carrega todos",
    )
    parser.add_argument(
        "--apenas-planilhas",
        type=Path,
        metavar="PASTA",
        help="Só grava os .xlsx nesta pasta, sem chamar a API",
    )
    args = parser.parse_args()

    meses, empresas = carregar_catalogo()
    if args.empresa:
        conhecidos = {e["slug"] for e in empresas}
        if desconhecidos := set(args.empresa) - conhecidos:
            raise SystemExit(
                f"slug desconhecido: {', '.join(sorted(desconhecidos))}. "
                f"Disponíveis: {', '.join(sorted(conhecidos))}"
            )
        empresas = [e for e in empresas if e["slug"] in args.empresa]

    if args.apenas_planilhas:
        args.apenas_planilhas.mkdir(parents=True, exist_ok=True)
        gravadas = 0
        for e in empresas:
            for periodo in meses:
                destino = args.apenas_planilhas / f"{e['slug']}-{periodo}"
                if periodo in e["teorico"]:
                    destino.with_name(destino.name + "-teorico.xlsx").write_bytes(
                        planilha_teorico(e["teorico"][periodo])
                    )
                    gravadas += 1
                if periodo in e["real"]:
                    destino.with_name(destino.name + "-real.xlsx").write_bytes(
                        planilha_real(e["real"][periodo])
                    )
                    gravadas += 1
        print(f"{gravadas} planilhas gravadas em {args.apenas_planilhas}")
        return

    api = args.api.rstrip("/")
    print(f"API: {api}")
    print(f"{len(empresas)} unidade(s) de demonstração, {len(meses)} meses cada\n")

    resumo = []
    for e in empresas:
        print(f"{e['nome']}  [{e['ramo']}]")
        casa_id = garantir_casa(api, e)
        total = uploads = 0
        for periodo in meses:
            if periodo in e["teorico"]:
                total += enviar(
                    api, casa_id, periodo, "cardapio", planilha_teorico(e["teorico"][periodo])
                )
                uploads += 1
            if periodo in e["real"]:
                total += enviar(api, casa_id, periodo, "compras", planilha_real(e["real"][periodo]))
                uploads += 1
        print(f"  {uploads} uploads, {total} linhas\n")
        resumo.append((e["nome"], e["ramo"], casa_id))

    print("Pronto. Unidades carregadas:")
    for nome, ramo, casa_id in resumo:
        print(f"  id {casa_id:<4} {ramo:<26} {nome}")
    print(
        f"\nConfira o fechamento de {meses[-1]} de qualquer uma:\n"
        f"  {api}/api/v1/metricas/fechamento?casa_id=<id>&periodo={meses[-1]}\n"
        f"  {api}/api/v1/metricas/recomendacao-compra?casa_id=<id>&periodo={meses[-1]}"
    )


if __name__ == "__main__":
    main()
