import { useState } from "react";
import { api, ApiError, type Casa, type MargemItem, type MargemItens as Dados } from "../api";

// Margem por item. O fechamento diz QUE um grupo saiu do previsto; esta tela
// diz QUAL item perdeu margem e quanto isso custou em reais — que é a unidade
// em que o sócio decide (preço, fornecedor, receita, cardápio). Usa só o
// cardápio, então funciona sem estoque e sem o lado real.

const POR_PAGINA = 20;

const reais = (n: number) =>
  n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

const pct = (n: number) => `${n.toFixed(1).replace(".", ",")}%`;

const variacao = (n: number | null) => {
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(0)}%`;
};

const mesAno = (periodo: string) => {
  const [ano, mes] = periodo.split("-");
  return `${mes}/${ano.slice(2)}`;
};

/** Mini-gráfico do CMV do item, do mês-base ao mês. Só a forma: subindo aos
 *  poucos (insumo encarecendo) é diferente de um pico num mês só (erro de
 *  ficha ou de lançamento). Os números estão nas colunas ao lado. */
function FaiscaCmv({ serie }: { serie: MargemItem["serie"] }) {
  const pontos = serie.filter((p): p is { periodo: string; cmv_pct: number } => p.cmv_pct !== null);
  if (pontos.length < 2) return <span className="faisca-vazia">—</span>;

  const largura = 96;
  const altura = 26;
  const valores = pontos.map((p) => p.cmv_pct);
  const max = Math.max(...valores);
  const min = Math.min(...valores);
  const amplitude = max - min || 1;
  const x = (i: number) => (i / (pontos.length - 1)) * largura;
  const y = (v: number) => altura - 2 - ((v - min) / amplitude) * (altura - 4);
  const ultimo = pontos[pontos.length - 1];

  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className="faisca"
      role="img"
      aria-label={`CMV do item de ${pct(pontos[0].cmv_pct)} a ${pct(ultimo.cmv_pct)}`}
    >
      <polyline
        points={pontos.map((p, i) => `${x(i)},${y(p.cmv_pct)}`).join(" ")}
        className="faisca-linha"
        fill="none"
      />
      <circle cx={x(pontos.length - 1)} cy={y(ultimo.cmv_pct)} r="2.2" className="faisca-ponta" />
    </svg>
  );
}

/** A frase que o sócio lê primeiro: o item que mais custou, e por quê. */
function Leitura({ dados }: { dados: Dados }) {
  const pior = dados.items[0];
  if (dados.itens_que_pioraram === 0 || !pior || pior.custo_extra <= 0) {
    return (
      <p>
        Nenhum item perdeu mais de {dados.limiar_pp.toFixed(0)} ponto de margem entre{" "}
        {mesAno(dados.periodo_base)} e {mesAno(dados.periodo)}.
      </p>
    );
  }
  const custo = variacao(pior.variacao_custo_pct);
  const preco = variacao(pior.variacao_preco_pct);
  return (
    <p>
      O maior impacto é <strong>{pior.nome}</strong>: o custo por unidade variou {custo} e o
      preço {preco}. Em {mesAno(dados.periodo)}, custou <strong>{reais(pior.custo_extra)}</strong>{" "}
      a mais do que custaria com a margem de {mesAno(dados.periodo_base)}.
    </p>
  );
}

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function MargemItens({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [base, setBase] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erroCalculado, setErro] = useState<string | null>(null);
  const [dadosCalculados, setDados] = useState<Dados | null>(null);
  // Mesmo cuidado da tela "Quanto comprar": resultado e erro são de uma casa e
  // de um mês, e não aparecem depois de trocar a seleção.
  const [calculadoPara, setCalculadoPara] = useState("");
  const atual = calculadoPara === `${casaId}|${periodo}|${base}`;
  const erro = atual ? erroCalculado : null;
  const dados = atual ? dadosCalculados : null;

  async function buscar(ev: React.FormEvent) {
    ev.preventDefault();
    if (casaId === "" || !periodo) return;
    setCarregando(true);
    setErro(null);
    setDados(null);
    setCalculadoPara(`${casaId}|${periodo}|${base}`);
    try {
      setDados(await api.margemItens(casaId, periodo, base, POR_PAGINA, 0));
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível calcular a margem por item.");
    } finally {
      setCarregando(false);
    }
  }

  async function mostrarMais() {
    if (!dados || casaId === "") return;
    setCarregando(true);
    try {
      const proxima = await api.margemItens(
        casaId,
        periodo,
        base,
        POR_PAGINA,
        dados.items.length,
      );
      setDados({ ...dados, items: [...dados.items, ...proxima.items] });
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível carregar mais itens.");
    } finally {
      setCarregando(false);
    }
  }

  const classeVariacao = (pp: number) =>
    dados && pp >= dados.limiar_pp ? "txt-ruim" : dados && pp <= -dados.limiar_pp ? "txt-bom" : "";

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Margem por item</h2>
        <p className="ajuda">
          Onde o cardápio perdeu margem, item por item, em reais. Compara cada item com ele mesmo
          num mês anterior — por padrão, o mesmo mês do ano passado.
        </p>
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
          <input
            type="month"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            required
          />
        </label>
        <label className="campo">
          <span className="campo-rotulo">Comparar com (opcional)</span>
          <input type="month" value={base} onChange={(e) => setBase(e.target.value)} />
        </label>
        <button type="submit" className="botao-primario" disabled={carregando}>
          {carregando ? "Calculando…" : "Calcular"}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}

      {dados && (
        <>
          <div className="hero-ajuste glass">
            <div
              className={`hero-selo ${dados.itens_que_pioraram > 0 ? "hero-selo-ruim" : "hero-selo-bom"}`}
            >
              {dados.itens_que_pioraram > 0
                ? `${dados.itens_que_pioraram} de ${dados.itens_comparados} itens perderam margem`
                : "Nenhum item perdeu margem"}
            </div>
            <span className="hero-rotulo">
              Custo extra em {mesAno(dados.periodo)} · {dados.casa_nome}
            </span>
            <strong className="hero-valor">{reais(dados.custo_extra_total)}</strong>
            <span className="hero-detalhe">
              comparado com {mesAno(dados.periodo_base)} ({dados.criterio_base})
            </span>
          </div>

          <div className="glass bloco-previsao">
            <Leitura dados={dados} />
            <p className="previsao-metodo">
              <strong>O que fazer com um item da lista:</strong> reajustar o preço, renegociar o
              insumo com o fornecedor, revisar a receita ou a ficha técnica, ou tirar do cardápio.
              Quem decide é a casa; a lista diz por onde começar.
            </p>
            <p className="previsao-aviso">
              <strong>Importante:</strong> {dados.aviso}
            </p>
          </div>

          {dados.items.length === 0 ? (
            <p className="vazio">Nenhum item vendido nos dois meses com venda suficiente.</p>
          ) : (
            <table className="tabela glass">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>CMV no período</th>
                  <th>
                    CMV {mesAno(dados.periodo_base)} → {mesAno(dados.periodo)}
                  </th>
                  <th>Custo por unidade</th>
                  <th>Preço</th>
                  <th>Custo extra no mês</th>
                </tr>
              </thead>
              <tbody>
                {dados.items.map((item) => (
                  <tr key={item.nome}>
                    <td>
                      <strong>{item.nome}</strong>
                      <span className="celula-fraca">
                        {item.grupo}
                        {item.subgrupo ? ` · ${item.subgrupo}` : ""}
                      </span>
                    </td>
                    <td className="celula-faisca">
                      <FaiscaCmv serie={item.serie} />
                    </td>
                    <td className="num">
                      {pct(item.cmv_base_pct)} → {pct(item.cmv_atual_pct)}
                      <span className={`celula-fraca ${classeVariacao(item.variacao_pp)}`}>
                        {item.variacao_pp > 0 ? "+" : ""}
                        {item.variacao_pp.toFixed(1).replace(".", ",")} pp
                      </span>
                    </td>
                    <td
                      className="num"
                      title={`${reais(item.custo_unitario_base)} → ${reais(item.custo_unitario_atual)}`}
                    >
                      {variacao(item.variacao_custo_pct)}
                    </td>
                    <td
                      className="num"
                      title={`${reais(item.preco_unitario_base)} → ${reais(item.preco_unitario_atual)}`}
                    >
                      {variacao(item.variacao_preco_pct)}
                    </td>
                    <td
                      className={`num ${item.custo_extra > 0 ? "num-destaque" : "txt-neutro"}`}
                    >
                      {reais(item.custo_extra)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {dados.items.length < dados.total && (
            <button
              type="button"
              className="botao-secundario"
              onClick={mostrarMais}
              disabled={carregando}
            >
              {carregando ? "Carregando…" : `Mostrar mais (${dados.total - dados.items.length})`}
            </button>
          )}

          <p className="ajuda">
            Ordenado pelo custo extra: quanto o item custou a mais no mês do que custaria se tivesse
            mantido o CMV de {mesAno(dados.periodo_base)}. Negativo = ficou mais barato. Ficam fora
            itens que não venderam nos dois meses ou venderam menos de{" "}
            {reais(dados.venda_minima)}. "Perdeu margem" = CMV subiu {dados.limiar_pp.toFixed(0)}{" "}
            ponto ou mais — premissa nossa. Passe o mouse no custo e no preço para ver os valores.
          </p>
        </>
      )}
    </section>
  );
}
