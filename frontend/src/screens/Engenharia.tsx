import { useState } from "react";
import {
  api,
  ApiError,
  type Casa,
  type ClasseCardapio,
  type EngenhariaCardapio,
  type ItemEngenharia,
} from "../api";

// Engenharia de cardápio (RF16): a matriz popularidade × margem de Kasavana &
// Smith. Substitui "Quanto comprar" (RF07), que previa a venda e, testada
// contra o histórico, não acertava mais que repetir o mês passado. Aqui não
// há previsão: é o que cada item vendeu e quanto deixou de margem no mês.

const POR_PAGINA = 200;

const reais = (n: number) =>
  n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 });
const reaisInteiro = (n: number) =>
  n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const pct = (n: number) => `${n.toFixed(1).replace(".", ",")}%`;
const num = (n: number) => n.toLocaleString("pt-BR", { maximumFractionDigits: 0 });

const mesAno = (periodo: string) => {
  const [ano, mes] = periodo.split("-");
  return `${mes}/${ano.slice(2)}`;
};

const QUADRANTES: Record<
  ClasseCardapio,
  { titulo: string; regra: string; acao: string; classe: string }
> = {
  quebra_cabeca: {
    titulo: "Quebra-cabeça",
    regra: "margem alta, vende pouco",
    acao: "Promover: destacar no cardápio, sugestão do garçom, rever o nome ou a foto.",
    classe: "quadrante-quebra",
  },
  estrela: {
    titulo: "Estrela",
    regra: "margem alta, vende muito",
    acao: "Manter e proteger: não mexer na receita nem no preço sem motivo.",
    classe: "quadrante-estrela",
  },
  cao: {
    titulo: "Cão",
    regra: "margem baixa, vende pouco",
    acao: "Reformular ou tirar do cardápio.",
    classe: "quadrante-cao",
  },
  burro_de_carga: {
    titulo: "Burro de carga",
    regra: "margem baixa, vende muito",
    acao: "Reajustar o preço ou a porção: cada centavo vezes muitas unidades.",
    classe: "quadrante-burro",
  },
};

// Ordem da matriz na tela: margem alta em cima, popular à direita.
const ORDEM_MATRIZ: ClasseCardapio[] = ["quebra_cabeca", "estrela", "cao", "burro_de_carga"];

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function Engenharia({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [carregando, setCarregando] = useState(false);
  const [erroCalculado, setErro] = useState<string | null>(null);
  const [resumoCalculado, setResumo] = useState<EngenhariaCardapio | null>(null);
  const [grupo, setGrupo] = useState("");
  const [itens, setItens] = useState<ItemEngenharia[]>([]);
  const [quadrante, setQuadrante] = useState<ClasseCardapio>("burro_de_carga");
  // Resultado e erro valem para a casa e o mês do cálculo, como nas outras telas.
  const [calculadoPara, setCalculadoPara] = useState("");
  const atual = calculadoPara === `${casaId}|${periodo}`;
  const erro = atual ? erroCalculado : null;
  const resumo = atual ? resumoCalculado : null;

  async function carregarGrupo(id: number, nome: string) {
    setGrupo(nome);
    setItens([]);
    try {
      setItens((await api.engenhariaCardapio(id, periodo, nome, POR_PAGINA, 0)).items);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível carregar os itens.");
    }
  }

  async function buscar(ev: React.FormEvent) {
    ev.preventDefault();
    if (casaId === "" || !periodo) return;
    setCarregando(true);
    setErro(null);
    setResumo(null);
    setItens([]);
    setCalculadoPara(`${casaId}|${periodo}`);
    try {
      const dados = await api.engenhariaResumo(casaId, periodo);
      setResumo(dados);
      if (dados.grupos.length > 0) await carregarGrupo(casaId, dados.grupos[0].grupo);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível calcular a engenharia.");
    } finally {
      setCarregando(false);
    }
  }

  const doGrupo = resumo?.grupos.find((g) => g.grupo === grupo);
  const doQuadrante = itens.filter((i) => i.classe === quadrante);

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Engenharia de cardápio</h2>
        <p className="ajuda">
          Cada item do mês no seu quadrante: quanto vende e quanto deixa de margem por unidade,
          comparado com os outros itens do mesmo grupo. Cada quadrante tem uma ação.
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
        <button type="submit" className="botao-primario" disabled={carregando}>
          {carregando ? "Calculando…" : "Calcular"}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}

      {resumo && (
        <>
          {/* Vendido abaixo do custo vem antes de tudo: é dinheiro saindo a cada
              unidade vendida, e quase sempre é ficha ou preço desatualizado. */}
          {resumo.abaixo_do_custo.length > 0 && (
            <div className="aviso aviso-dado">
              <strong>
                {resumo.abaixo_do_custo.length === 1
                  ? "1 item vendido abaixo do custo"
                  : `${resumo.abaixo_do_custo.length} itens vendidos abaixo do custo`}{" "}
                em {mesAno(resumo.periodo)}:
              </strong>{" "}
              {resumo.abaixo_do_custo.map((i, n) => (
                <span key={i.nome}>
                  {n > 0 && "; "}
                  {i.nome} ({reais(i.margem_unitaria)} por unidade, {num(i.quantidade)} vendidas)
                </span>
              ))}
              . Confira a ficha técnica e o preço de venda.
            </div>
          )}

          <div className="segmentado" role="radiogroup" aria-label="Grupo">
            {resumo.grupos.map((g) => (
              <button
                key={g.grupo}
                type="button"
                role="radio"
                aria-checked={g.grupo === grupo}
                className={g.grupo === grupo ? "segmento segmento-ativo" : "segmento"}
                onClick={() => casaId !== "" && carregarGrupo(casaId, g.grupo)}
              >
                <strong>{g.grupo}</strong>
                <span>
                  {g.itens} itens · margem média {reais(g.margem_media_unitaria)} por unidade
                </span>
              </button>
            ))}
          </div>

          {doGrupo && (
            <>
              <div className="matriz" role="radiogroup" aria-label="Quadrante">
                <span className="matriz-eixo matriz-eixo-y">margem por unidade ↑</span>
                {ORDEM_MATRIZ.map((classe) => {
                  const q = QUADRANTES[classe];
                  const nomes = itens
                    .filter((i) => i.classe === classe)
                    .slice(0, 3)
                    .map((i) => i.nome);
                  return (
                    <button
                      key={classe}
                      type="button"
                      role="radio"
                      aria-checked={classe === quadrante}
                      className={`quadrante glass ${q.classe} ${
                        classe === quadrante ? "quadrante-ativo" : ""
                      }`}
                      onClick={() => setQuadrante(classe)}
                    >
                      <span className="quadrante-topo">
                        <strong>{q.titulo}</strong>
                        <span className="quadrante-n">{doGrupo[classe]}</span>
                      </span>
                      <span className="quadrante-regra">{q.regra}</span>
                      <span className="quadrante-acao">{q.acao}</span>
                      {nomes.length > 0 && (
                        <span className="quadrante-itens">{nomes.join(" · ")}</span>
                      )}
                    </button>
                  );
                })}
                <span className="matriz-eixo matriz-eixo-x">vende mais →</span>
              </div>

              <h3 className="titulo-secao">
                {QUADRANTES[quadrante].titulo} · {grupo} · {doQuadrante.length}{" "}
                {doQuadrante.length === 1 ? "item" : "itens"}
              </h3>
              {doQuadrante.length === 0 ? (
                <p className="vazio">Nenhum item deste grupo neste quadrante.</p>
              ) : (
                <table className="tabela glass">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Vendidas</th>
                      <th>Preço médio</th>
                      <th>Custo por unidade</th>
                      <th>Margem por unidade</th>
                      <th>Margem no mês</th>
                    </tr>
                  </thead>
                  <tbody>
                    {doQuadrante.map((item) => (
                      <tr key={item.nome}>
                        <td>
                          <strong>{item.nome}</strong>
                          <span className="celula-fraca">
                            {item.subgrupo ?? item.grupo} · CMV {pct(item.cmv_pct)}
                          </span>
                        </td>
                        <td className="num">
                          {num(item.quantidade)}
                          <span className="celula-fraca">
                            {pct(item.popularidade_pct)} do grupo
                          </span>
                        </td>
                        <td className="num">{reais(item.preco_medio)}</td>
                        <td className="num">{reais(item.custo_unitario)}</td>
                        <td
                          className={`num ${
                            item.margem_unitaria < 0
                              ? "txt-ruim"
                              : item.margem_unitaria >= doGrupo.margem_media_unitaria
                                ? "txt-bom"
                                : ""
                          }`}
                        >
                          {reais(item.margem_unitaria)}
                        </td>
                        <td className="num num-destaque">{reaisInteiro(item.margem_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <p className="ajuda">
                <strong>Como lemos:</strong> {resumo.metodo} Em {grupo}: margem média de{" "}
                {reais(doGrupo.margem_media_unitaria)} por unidade; popular = pelo menos{" "}
                {pct(doGrupo.limiar_popularidade_pct)} das unidades do grupo. {resumo.aviso}
              </p>
            </>
          )}
        </>
      )}
    </section>
  );
}
