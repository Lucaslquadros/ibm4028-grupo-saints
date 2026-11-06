import { useState } from "react";
import { api, ApiError, type Casa, type PrevisaoItem, type RecomendacaoCompra } from "../api";

const num = (n: number) =>
  n.toLocaleString("pt-BR", { maximumFractionDigits: 0 });

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

/** "2026-10" → "outubro". O período vem como AAAA-MM e ninguém lê "mês 10". */
const nomeDoMes = (periodo: string) => MESES[Number(periodo.slice(5, 7)) - 1] ?? periodo;

const CONFIANCA: Record<PrevisaoItem["confianca"], { rotulo: string; classe: string }> = {
  alta: { rotulo: "Alta", classe: "selo-conf selo-conf-alta" },
  media: { rotulo: "Média", classe: "selo-conf selo-conf-media" },
  baixa: { rotulo: "Baixa", classe: "selo-conf selo-conf-baixa" },
};

/** Mini-gráfico do histórico de venda do item. Não tem eixo nem número: serve
 *  para a pessoa ver a FORMA da série (subindo, caindo, serrilhada) antes de
 *  confiar na previsão. Número exato já está na tabela. */
function Faisca({ pontos }: { pontos: { periodo: string; quantidade: number }[] }) {
  if (pontos.length < 2) return <span className="faisca-vazia">—</span>;

  const largura = 96;
  const altura = 26;
  const valores = pontos.map((p) => p.quantidade);
  const max = Math.max(...valores);
  const min = Math.min(...valores);
  const amplitude = max - min || 1;

  const x = (i: number) => (i / (pontos.length - 1)) * largura;
  const y = (v: number) => altura - 2 - ((v - min) / amplitude) * (altura - 4);

  const linha = pontos.map((p, i) => `${x(i)},${y(p.quantidade)}`).join(" ");
  const ultimo = pontos[pontos.length - 1];

  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className="faisca"
      role="img"
      aria-label={`Histórico de ${pontos.length} meses, de ${num(pontos[0].quantidade)} a ${num(ultimo.quantidade)} unidades`}
    >
      <polyline points={linha} className="faisca-linha" fill="none" />
      <circle cx={x(pontos.length - 1)} cy={y(ultimo.quantidade)} r="2.2" className="faisca-ponta" />
    </svg>
  );
}

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function Recomendacao({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [margem, setMargem] = useState(10);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [dados, setDados] = useState<RecomendacaoCompra | null>(null);

  async function buscar(ev: React.FormEvent) {
    ev.preventDefault();
    if (casaId === "" || !periodo) return;
    setCarregando(true);
    setErro(null);
    setDados(null);
    try {
      setDados(await api.recomendacaoCompra(casaId, periodo, margem, 10));
    } catch (e) {
      setErro(
        e instanceof ApiError ? e.message : "Não foi possível calcular a recomendação.",
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Quanto comprar</h2>
        <p className="ajuda">
          Demanda esperada do mês seguinte, a partir do histórico de venda já carregado.
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
          <span className="campo-rotulo">Último mês com dado</span>
          <input
            type="month"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            required
          />
        </label>
        <label className="campo">
          <span className="campo-rotulo">Margem de segurança</span>
          <div className="campo-margem">
            <input
              type="range"
              min={0}
              max={50}
              step={5}
              value={margem}
              onChange={(e) => setMargem(Number(e.target.value))}
            />
            <output>{margem}%</output>
          </div>
        </label>
        <button type="submit" className="botao-primario" disabled={carregando}>
          {carregando ? "Calculando…" : "Calcular"}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}

      {dados && (
        <>
          {/* O alerta de dado suspeito vem ANTES de qualquer número: se o mês-base
              estiver incompleto, toda a tabela abaixo está subestimada, e quem lê
              precisa saber disso primeiro. */}
          {dados.alerta_dado && (
            <p className="aviso aviso-dado">
              <strong>Atenção ao dado de entrada.</strong> {dados.alerta_dado}
            </p>
          )}

          <div className="glass bloco-previsao">
            <div className="previsao-cabecalho">
              <span className="hero-rotulo">
                Previsão para {dados.periodo_alvo} · {dados.casa_nome}
              </span>
              <span className="previsao-base">
                a partir do histórico até {dados.periodo_base}
              </span>
            </div>
            {/* Método e limite ficam junto do número, não num rodapé. Número de
                compra sem a ressalva de que ignora o estoque atual é número que
                faz alguém comprar errado. */}
            <p className="previsao-metodo">{dados.metodo}</p>
            <p className="previsao-aviso">
              <strong>Importante:</strong> {dados.aviso}
            </p>
          </div>

          {dados.itens.length === 0 ? (
            <p className="vazio">Nenhum item com histórico de venda neste período.</p>
          ) : (
            <table className="tabela glass">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Histórico</th>
                  <th>Média 3 meses</th>
                  <th>Tendência</th>
                  <th>Efeito do mês</th>
                  <th>Demanda prevista</th>
                  <th>Sugestão de compra</th>
                  <th>Confiança</th>
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((item) => (
                  <tr key={item.nome}>
                    <td>
                      <strong>{item.nome}</strong>
                      <span className="celula-fraca">
                        {item.grupo}
                        {item.subgrupo ? ` · ${item.subgrupo}` : ""}
                      </span>
                    </td>
                    <td className="celula-faisca">
                      <Faisca pontos={item.historico} />
                      <span className="celula-fraca">{item.meses_com_dado} meses</span>
                    </td>
                    <td className="num">{num(item.media_recente)}</td>
                    <td
                      className={`num ${
                        item.tendencia_pct === null
                          ? ""
                          : item.tendencia_pct >= 0
                            ? "txt-bom"
                            : "txt-ruim"
                      }`}
                    >
                      {item.tendencia_pct === null ? (
                        <span title="Histórico curto demais para medir tendência">—</span>
                      ) : (
                        `${item.tendencia_pct > 0 ? "+" : ""}${item.tendencia_pct.toFixed(1)}%`
                      )}
                    </td>
                    {/* Sem esta coluna a tabela fica inexplicável nos casos que
                        mais importam: um item com média 52 e sugestão 93 parece
                        erro, até se ver que aquele mês historicamente vende 33%
                        acima da média. O índice é o que justifica a diferença. */}
                    <td className="num">
                      {item.indice_sazonal === null ? (
                        <span title="Menos de um ano de histórico — sem base para efeito de mês">
                          —
                        </span>
                      ) : (
                        <span
                          title={`Em ${nomeDoMes(dados.periodo_alvo)}, este item costuma vender ${
                            item.indice_sazonal >= 1 ? "acima" : "abaixo"
                          } da média anual. Índice ${item.indice_sazonal.toFixed(2)}`}
                        >
                          {item.indice_sazonal > 1 ? "+" : ""}
                          {((item.indice_sazonal - 1) * 100).toFixed(0)}%
                        </span>
                      )}
                    </td>
                    <td className="num">{num(item.demanda_prevista)}</td>
                    <td className="num num-destaque">{num(item.sugestao_compra)}</td>
                    <td>
                      <span
                        className={CONFIANCA[item.confianca].classe}
                        title={item.motivo_confianca}
                      >
                        {CONFIANCA[item.confianca].rotulo}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {dados.itens.length > 0 && (
            <p className="ajuda">
              Passe o mouse sobre a confiança para ver por que ela é essa. A sugestão já
              inclui a margem de {dados.margem_seguranca_pct}%.
            </p>
          )}
        </>
      )}
    </section>
  );
}
