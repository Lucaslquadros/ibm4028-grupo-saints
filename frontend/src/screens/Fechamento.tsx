import { useState } from "react";
import {
  api,
  ApiError,
  type Acumulado,
  type BaseReal,
  type Casa,
  type Explicacao,
  type Fechamento as FechamentoDto,
  type ItemCardapio,
  type PontoEvolucao,
  type SituacaoAjuste,
} from "../api";

const brl = (n: number | null) =>
  n === null ? "—" : n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const pct = (n: number | null) => (n === null ? "—" : `${n.toFixed(2)}%`);

// Pontos percentuais não são por cento: 3 pp de diferença entre dois CMV% não
// é "3%". O sinal vem sempre explícito, porque é ele que muda o diagnóstico.
const pp = (n: number | null) => (n === null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)} pp`);

// As três situações do RF11. Ajuste negativo NÃO é economia — é divergência,
// normalmente algo faltando no lado real. Por isso "abaixo" é atenção (âmbar),
// e não o verde de "favorável" que esta tela mostrava antes.
const SELO: Record<SituacaoAjuste, { rotulo: string; classe: string }> = {
  acima: { rotulo: "Acima do previsto", classe: "hero-selo-ruim" },
  dentro: { rotulo: "Dentro da margem", classe: "hero-selo-bom" },
  abaixo: { rotulo: "Abaixo do previsto", classe: "hero-selo-atencao" },
};

// O cabeçalho da coluna do lado real diz o que ela é. A DRE do Everest é
// compras do mês, não consumo: chamá-la de "Real" foi o que fez o −3,68 pp de
// set/26 parecer um desvio (ver docs/07-fechamento-cmv.md, 10/11/2026).
const LADO_REAL: Record<BaseReal, { titulo: string; fonte: string }> = {
  consumo: { titulo: "Real", fonte: "estoque inicial + compras − final" },
  compras: { titulo: "Compras", fonte: "DRE, sem estoque" },
  declarada: { titulo: "Real", fonte: "informado na planilha" },
};

const mesAno = (periodo: string) => {
  const [ano, mes] = periodo.split("-");
  return `${mes}/${ano.slice(2)}`;
};

function classeDoAjuste(valor: number | null, limiar: number) {
  if (valor === null) return "";
  if (valor > limiar) return "txt-ruim";
  if (valor < -limiar) return "txt-atencao";
  return "txt-neutro";
}

function EvolucaoChart({ pontos }: { pontos: PontoEvolucao[] }) {
  const comDado = pontos.filter((p) => p.cmv_teorico_pct !== null || p.cmv_real_pct !== null);
  if (comDado.length === 0) return <p className="vazio">Sem dado suficiente para o gráfico.</p>;

  const largura = 640;
  const altura = 220;
  const margem = { topo: 16, baixo: 28, esquerda: 40, direita: 16 };
  const valores = comDado.flatMap((p) => [p.cmv_teorico_pct, p.cmv_real_pct]).filter(
    (v): v is number => v !== null,
  );
  const max = Math.max(...valores, 10);
  const min = Math.min(0, Math.min(...valores));

  const x = (i: number) =>
    margem.esquerda +
    (i / Math.max(1, comDado.length - 1)) * (largura - margem.esquerda - margem.direita);
  const y = (v: number) =>
    altura -
    margem.baixo -
    ((v - min) / (max - min || 1)) * (altura - margem.topo - margem.baixo);

  const linha = (campo: "cmv_teorico_pct" | "cmv_real_pct") =>
    comDado
      .map((p, i) => (p[campo] === null ? null : `${x(i)},${y(p[campo] as number)}`))
      .filter((v): v is string => v !== null)
      .join(" ");

  const passo = Math.max(1, Math.ceil(comDado.length / 10));

  return (
    <svg viewBox={`0 0 ${largura} ${altura}`} className="grafico" role="img" aria-label="Evolução do CMV teórico e real">
      <line x1={margem.esquerda} x2={largura - margem.direita} y1={y(0)} y2={y(0)} className="grafico-eixo" />
      <polyline points={linha("cmv_teorico_pct")} className="grafico-linha grafico-teorico" fill="none" />
      <polyline points={linha("cmv_real_pct")} className="grafico-linha grafico-real" fill="none" />
      {comDado.map((p, i) =>
        i % passo === 0 ? (
          <text key={p.periodo} x={x(i)} y={altura - 6} textAnchor="middle" className="grafico-rotulo">
            {p.periodo.slice(2)}
          </text>
        ) : null,
      )}
    </svg>
  );
}

/** O parágrafo que o sócio lê primeiro — vem ACIMA do número, de propósito:
 * o número ele já tem no ERP, a leitura é o que o sistema acrescenta. */
export function BlocoExplicacao({ explicacao }: { explicacao: Explicacao }) {
  return (
    // Sem selo de situação aqui: ele fica no hero logo abaixo, e repetir o
    // mesmo rótulo duas vezes em meia tela só rouba atenção do parágrafo.
    <div className="glass explicacao">
      <p className="explicacao-resumo">{explicacao.resumo}</p>
      {explicacao.sugestoes.length > 0 && (
        <>
          <span className="explicacao-rotulo">O que conferir</span>
          <ol className="sugestoes">
            {explicacao.sugestoes.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </>
      )}
      <p className="explicacao-premissa">
        Consideramos normal uma diferença de até {explicacao.limiar_pp.toFixed(1)} ponto. É uma
        premissa nossa, não um parâmetro do cliente.
      </p>
    </div>
  );
}

/** As categorias que existem num lado só — recolhidas por padrão.
 *
 * São o maior volume de número da tela e **não são desvio**: o ERP informa
 * compra por categoria de insumo e venda por categoria de cardápio. Ficam
 * disponíveis porque escondê-las seria esconder de que o custo é feito; ficam
 * fechadas porque ninguém decide nada olhando para elas.
 */
function ComposicaoDoCusto({ explicacao }: { explicacao: Explicacao }) {
  const semPar = explicacao.subgrupos_sem_par;
  if (semPar.length === 0) return null;

  return (
    <>
      {/* A tarja fica FORA do recolhível: é o motivo de a comparação por
          categoria vir curta, e precisa ser lida mesmo por quem não abrir. */}
      <p className="aviso">{explicacao.limite_dado}</p>
      <details className="composicao glass">
        <summary>
          Composição do custo — {semPar.length} categorias que existem em um lado só.{" "}
          <strong>Não são desvio.</strong>
        </summary>
        <table className="tabela tabela-embutida">
          <thead>
            <tr>
              <th>Grupo</th>
              <th>Categoria</th>
              <th>Lado</th>
              <th>Custo</th>
            </tr>
          </thead>
          <tbody>
            {semPar.map((s) => (
              <tr key={`${s.grupo}-${s.subgrupo}-${s.lado}`}>
                <td>{s.grupo}</td>
                <td>{s.subgrupo}</td>
                <td>{s.lado === "teorico" ? "Teórico (cardápio)" : "Real (compras)"}</td>
                <td className="num">{brl(s.custo)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}

/** O fechamento no formato de balanço: colunas são os dois lados, linhas são
 * as contas.
 *
 * A tabela anterior punha venda, CMV teórico, CMV real, ajuste e contribuição
 * lado a lado na mesma linha — e isso mistura os dois relatórios dentro de uma
 * linha só: "CMV real" é custo de **compras** dividido por receita de
 * **venda**. Correto no cálculo, ilegível na tela.
 *
 * Aqui a venda aparece uma vez, como base do grupo, e fica explícito que é o
 * MESMO denominador dos dois lados — que é justamente o que faz a diferença em
 * pontos ser só diferença de custo. Os subgrupos comparáveis entram aninhados,
 * como numa DRE, em vez de numa segunda tabela.
 */
function Balanco({
  dados,
  explicacao,
}: {
  dados: Pick<FechamentoDto, "grupos" | "total" | "base_real">;
  explicacao: Explicacao | null;
}) {
  const limiar = explicacao?.limiar_pp ?? 1;
  const ladoReal = LADO_REAL[dados.base_real ?? "declarada"];
  const temExplicacao = explicacao !== null;
  const subgruposDe = (grupo: string) =>
    (explicacao?.subgrupos_comparados ?? []).filter((s) => s.grupo === grupo);

  const bloco = (linha: FechamentoDto["total"], total = false) => {
    const subgrupos = total ? [] : subgruposDe(linha.grupo);
    return (
      <tbody key={linha.grupo} className={total ? "balanco-total" : undefined}>
        <tr className="balanco-grupo">
          <th scope="rowgroup" colSpan={2}>
            {linha.grupo}
          </th>
          <td className="num balanco-base" colSpan={2}>
            venda líquida {brl(linha.venda_liquida)}
          </td>
        </tr>
        <tr>
          <td className="balanco-conta" colSpan={1}>
            custo
          </td>
          <td className="num">{brl(linha.custo_teorico)}</td>
          <td className="num">{brl(linha.custo_real)}</td>
          <td className="num">{brl(linha.ajuste)}</td>
        </tr>
        <tr>
          <td className="balanco-conta">sobre a venda</td>
          <td className="num">{pct(linha.cmv_teorico_pct)}</td>
          <td className="num">{pct(linha.cmv_real_pct)}</td>
          <td className={`num ${classeDoAjuste(linha.ajuste_pp, limiar)}`}>{pp(linha.ajuste_pp)}</td>
        </tr>
        {subgrupos.map((s) => (
          <tr key={s.subgrupo} className="balanco-sub">
            <td className="balanco-conta">{s.subgrupo}</td>
            <td className="num">{brl(s.custo_teorico)}</td>
            <td className="num">{brl(s.custo_real)}</td>
            <td className="num">
              {brl(s.ajuste)}
              {s.ajuste_pp !== null && <span className="balanco-pp">{pp(s.ajuste_pp)}</span>}
            </td>
          </tr>
        ))}
        {/* Sem esta linha, um grupo sem filhos parece dado faltando. Não é:
            é taxonomia que não se encontra nos dois relatórios. A tarja abaixo
            da tabela explica o porquê, mas ela está longe daqui. */}
        {!total && temExplicacao && subgrupos.length === 0 && (
          <tr className="balanco-sub">
            <td className="balanco-conta balanco-vazio" colSpan={4}>
              nenhuma categoria com o mesmo nome nos dois relatórios
            </td>
          </tr>
        )}
      </tbody>
    );
  };

  return (
    <table className="tabela balanco glass">
      <thead>
        <tr>
          <th />
          <th className="num">
            Teórico<span className="balanco-fonte">ficha técnica</span>
          </th>
          <th className="num">
            {ladoReal.titulo}
            <span className="balanco-fonte">{ladoReal.fonte}</span>
          </th>
          <th className="num">Diferença</th>
        </tr>
      </thead>
      {dados.grupos.map((g) => bloco(g))}
      {bloco(dados.total, true)}
    </table>
  );
}

/** Teórico × real somados nos meses com os dois lados.
 *
 * Sem inventário, é a única leitura do lado real que faz sentido: mês a mês a
 * diferença mistura desvio com o ritmo de compra e estoque (na casa piloto,
 * de −7,2 a +9,3 pp em jun–dez/22); somando meses, o estoque se dilui (+0,5 pp).
 */
function BlocoAcumulado({ acumulado }: { acumulado: Acumulado }) {
  const intervalo =
    acumulado.meses === 1
      ? mesAno(acumulado.periodo_inicio)
      : `${mesAno(acumulado.periodo_inicio)} a ${mesAno(acumulado.periodo_fim)}`;
  const faixa =
    acumulado.meses > 1 &&
    acumulado.ajuste_mensal_min_pp !== null &&
    acumulado.ajuste_mensal_max_pp !== null
      ? `Mês a mês, a diferença foi de ${pp(acumulado.ajuste_mensal_min_pp)} a ${pp(acumulado.ajuste_mensal_max_pp)}.`
      : null;

  return (
    <>
      <h3>
        Acumulado · {acumulado.meses} {acumulado.meses === 1 ? "mês" : "meses"} ({intervalo})
      </h3>
      <p className={acumulado.conclusivo ? "ajuda" : "aviso"}>
        {acumulado.conclusivo
          ? "Soma dos meses com os dois relatórios nos últimos 12 meses."
          : `Com o lado real só em compras, o acumulado precisa de pelo menos ${acumulado.meses_minimos} meses com os dois relatórios para a variação de estoque se diluir. Há ${acumulado.meses}: ainda não dá para concluir.`}{" "}
        {faixa}
      </p>
      <Balanco
        dados={{ grupos: acumulado.grupos, total: acumulado.total, base_real: acumulado.base_real }}
        explicacao={null}
      />
    </>
  );
}

/** O resultado do fechamento sem o formulário de busca.
 *
 * Extraído para o fluxo guiado "Fechar o mês" (RF12) mostrar exatamente o
 * mesmo painel do último passo, em vez de uma segunda versão do mesmo
 * cálculo que depois saísse do lugar.
 */
export function PainelFechamento({ dados }: { dados: FechamentoDto }) {
  // `explicacao` pode não existir: o backend em produção durante o deploy pode
  // ser a versão anterior. Sem ela a tela mostra o número sem leitura, nunca um
  // rótulo de valor ("favorável") que o sinal do ajuste não sustenta.
  const explicacao = dados.explicacao ?? null;
  // Lado real só em compras: o número do mês fica na tela para conferência,
  // mas o selo não pode dizer "acima/abaixo do previsto" como diagnóstico.
  const soCompras = dados.base_real === "compras" || explicacao?.conclusivo === false;
  const selo = soCompras
    ? { rotulo: "Inconclusivo · falta o estoque", classe: "" }
    : explicacao
      ? SELO[explicacao.situacao]
      : { rotulo: "Ajuste do mês", classe: "" };

  return (
    <>
      {(!dados.tem_cardapio || !dados.tem_compras) && (
        <p className="aviso">
          {!dados.tem_cardapio && "Falta o upload do cardápio (CMV teórico) deste período. "}
          {!dados.tem_compras && "Falta o upload do lado real (compras ou movimento de estoque) deste período."}
        </p>
      )}

      {explicacao && <BlocoExplicacao explicacao={explicacao} />}

      {/* O hero perdeu o par teórico × real: ele agora está no balanço, e
          repetido aqui eram seis números a mais dizendo a mesma coisa. */}
      <div className="hero-ajuste glass">
        <div className={`hero-selo ${selo.classe}`}>{selo.rotulo}</div>
        <span className="hero-rotulo">
          {soCompras ? "Compras × teórico do mês" : "Ajuste do mês"} · {dados.casa_nome}
        </span>
        <strong className="hero-valor">{pp(dados.total.ajuste_pp)}</strong>
        <span className="hero-detalhe">
          {brl(dados.total.ajuste)} de diferença entre {soCompras ? "compras" : "real"} e teórico
        </span>
      </div>

      <Balanco dados={dados} explicacao={explicacao} />

      {dados.acumulado && <BlocoAcumulado acumulado={dados.acumulado} />}

      {explicacao && <ComposicaoDoCusto explicacao={explicacao} />}
    </>
  );
}

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function Fechamento({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [dados, setDados] = useState<FechamentoDto | null>(null);
  const [evolucao, setEvolucao] = useState<PontoEvolucao[]>([]);
  const [topItens, setTopItens] = useState<ItemCardapio[]>([]);

  async function buscar(ev: React.FormEvent) {
    ev.preventDefault();
    if (casaId === "" || !periodo) return;
    setCarregando(true);
    setErro(null);
    setDados(null);
    try {
      const [fechamento, pontosEvolucao] = await Promise.all([
        api.fechamento(casaId, periodo),
        api.evolucao(casaId),
      ]);
      setDados(fechamento);
      setEvolucao(pontosEvolucao);
      setTopItens(fechamento.tem_cardapio ? await api.topItens(casaId, periodo) : []);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível calcular o fechamento.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Fechamento de CMV</h2>
        <p className="ajuda">Teórico × real × ajuste — e onde a diferença está.</p>
      </header>

      <form className="glass form-fechamento" onSubmit={buscar}>
        <label className="campo">
          <span className="campo-rotulo">Casa</span>
          <select
            value={casaId}
            onChange={(e) => setCasaId(e.target.value ? Number(e.target.value) : "")}
            required
          >
            <option value="">Selecione…</option>
            {casas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span className="campo-rotulo">Período</span>
          <input type="month" value={periodo} onChange={(e) => setPeriodo(e.target.value)} required />
        </label>
        <button type="submit" className="botao-primario" disabled={carregando}>
          {carregando ? "Calculando…" : "Calcular"}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}

      {dados && (
        <>
          <PainelFechamento dados={dados} />

          <h3>Evolução mensal</h3>
          <div className="legenda">
            <span className="legenda-item"><i className="grafico-teorico" /> Teórico</span>
            <span className="legenda-item"><i className="grafico-real" /> Real</span>
          </div>
          <div className="glass grafico-moldura">
            <EvolucaoChart pontos={evolucao} />
          </div>

          {topItens.length > 0 && (
            <>
              <h3>Top itens de maior custo</h3>
              <table className="tabela glass">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Grupo</th>
                    <th>Custo</th>
                    <th>CMV %</th>
                  </tr>
                </thead>
                <tbody>
                  {topItens.map((item) => (
                    <tr key={item.nome}>
                      <td>{item.nome}</td>
                      <td>{item.grupo}</td>
                      <td className="num">{brl(item.custo)}</td>
                      <td className="num">{pct(item.cmv_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </section>
  );
}
