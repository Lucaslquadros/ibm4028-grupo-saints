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
  const altura = 200;
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

  return (
    <svg viewBox={`0 0 ${largura} ${altura}`} className="grafico" role="img" aria-label="Evolução do CMV teórico e real">
      <line x1={margem.esquerda} x2={largura - margem.direita} y1={y(0)} y2={y(0)} className="grafico-eixo" />
      <polyline points={linha("cmv_teorico_pct")} className="grafico-linha grafico-teorico" fill="none" />
      <polyline points={linha("cmv_real_pct")} className="grafico-linha grafico-real" fill="none" />
      {comDado.map((p, i) => (
        <text key={p.periodo} x={x(i)} y={altura - 8} textAnchor="middle" className="grafico-rotulo">
          {p.periodo.slice(2)}
        </text>
      ))}
    </svg>
  );
}

export function Fechamento({ casas }: { casas: Casa[] }) {
  const [casaId, setCasaId] = useState<number | "">("");
  const [periodo, setPeriodo] = useState("");
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
    <section>
      <h2>Fechamento de CMV</h2>

      <form className="form-fechamento" onSubmit={buscar}>
        <label>
          Casa
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
        <label>
          Período (AAAA-MM)
          <input
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            placeholder="2026-09"
            pattern="\d{4}-(0[1-9]|1[0-2])"
            required
          />
        </label>
        <button type="submit" disabled={carregando}>
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

          <div className="cards">
            <div className="card">
              <span className="card-rotulo">CMV teórico</span>
              <strong>{pct(dados.total.cmv_teorico_pct)}</strong>
              <span>{brl(dados.total.custo_teorico)}</span>
            </div>
            <div className="card">
              <span className="card-rotulo">CMV real</span>
              <strong>{pct(dados.total.cmv_real_pct)}</strong>
              <span>{brl(dados.total.custo_real)}</span>
            </div>
            <div className={`card ${dados.total.ajuste_pp !== null && dados.total.ajuste_pp < 0 ? "card-bom" : "card-ruim"}`}>
              <span className="card-rotulo">Ajuste</span>
              <strong>
                {dados.total.ajuste_pp !== null && dados.total.ajuste_pp > 0 ? "+" : ""}
                {pct(dados.total.ajuste_pp)}
              </strong>
              <span>{brl(dados.total.ajuste)}</span>
            </div>
          </div>

          <table className="tabela">
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
                  <td>{brl(g.venda_liquida)}</td>
                  <td>{pct(g.cmv_teorico_pct)}</td>
                  <td>{pct(g.cmv_real_pct)}</td>
                  <td>{pct(g.ajuste_pp)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Evolução mensal</h3>
          <div className="legenda">
            <span className="legenda-item"><i className="grafico-teorico" /> Teórico</span>
            <span className="legenda-item"><i className="grafico-real" /> Real</span>
          </div>
          <EvolucaoChart pontos={evolucao} />

          {topItens.length > 0 && (
            <>
              <h3>Top itens de maior custo</h3>
              <table className="tabela">
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
                      <td>{brl(item.custo)}</td>
                      <td>{pct(item.cmv_pct)}</td>
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
