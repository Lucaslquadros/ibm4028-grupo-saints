import { useState } from "react";
import {
  api,
  ApiError,
  type Casa,
  type Fechamento as FechamentoDto,
  type ItemCardapio,
  type PontoEvolucao,
} from "../api";

const brl = (n: number | null) =>
  n === null ? "—" : n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const pct = (n: number | null) => (n === null ? "—" : `${n.toFixed(2)}%`);

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

  const ajuste = dados?.total.ajuste_pp ?? null;
  const favoravel = ajuste !== null && ajuste <= 0;

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Fechamento de CMV</h2>
        <p className="ajuda">Teórico × real × ajuste — o relatório que hoje leva dois dias por casa.</p>
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
          {(!dados.tem_cardapio || !dados.tem_compras) && (
            <p className="aviso">
              {!dados.tem_cardapio && "Falta o upload do cardápio (CMV teórico) deste período. "}
              {!dados.tem_compras && "Falta o upload de compras (CMV real) deste período."}
            </p>
          )}

          <div className="hero-ajuste glass">
            <div className={favoravel ? "hero-selo hero-selo-bom" : "hero-selo hero-selo-ruim"}>
              {ajuste === null ? "—" : favoravel ? "Favorável" : "Desfavorável"}
            </div>
            <span className="hero-rotulo">Ajuste do mês · {dados.casa_nome}</span>
            <strong className="hero-valor">
              {ajuste !== null && ajuste > 0 ? "+" : ""}
              {pct(ajuste)}
            </strong>
            <span className="hero-detalhe">{brl(dados.total.ajuste)} de diferença entre real e teórico</span>

            <div className="hero-lado">
              <div>
                <span className="hero-lado-k">Teórico</span>
                <span className="hero-lado-v">{pct(dados.total.cmv_teorico_pct)}</span>
                <span className="hero-lado-d">{brl(dados.total.custo_teorico)}</span>
              </div>
              <div className="hero-lado-sep" />
              <div>
                <span className="hero-lado-k">Real</span>
                <span className="hero-lado-v">{pct(dados.total.cmv_real_pct)}</span>
                <span className="hero-lado-d">{brl(dados.total.custo_real)}</span>
              </div>
            </div>
          </div>

          <table className="tabela glass">
            <thead>
              <tr>
                <th>Grupo</th>
                <th>Venda líquida</th>
                <th>CMV teórico</th>
                <th>CMV real</th>
                <th>Ajuste</th>
              </tr>
            </thead>
            <tbody>
              {dados.grupos.map((g) => (
                <tr key={g.grupo}>
                  <td>{g.grupo}</td>
                  <td className="num">{brl(g.venda_liquida)}</td>
                  <td className="num">{pct(g.cmv_teorico_pct)}</td>
                  <td className="num">{pct(g.cmv_real_pct)}</td>
                  <td className={`num ${g.ajuste_pp !== null && g.ajuste_pp <= 0 ? "txt-bom" : "txt-ruim"}`}>
                    {pct(g.ajuste_pp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

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
