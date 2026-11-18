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

/** Vendido abaixo do custo vem antes de tudo: é dinheiro saindo a cada unidade
 *  vendida, e quase sempre é ficha ou preço desatualizado. Conta TODOS os itens
 *  do mês, inclusive os que vendem pouco demais para entrar na matriz. */
function AlertaAbaixoDoCusto({ resumo }: { resumo: EngenhariaCardapio }) {
  const total = resumo.abaixo_do_custo_total ?? resumo.abaixo_do_custo.length;
  const prejuizo =
    resumo.abaixo_do_custo_prejuizo ??
    resumo.abaixo_do_custo.reduce((soma, i) => soma + i.margem_total, 0);
  const mostrados = resumo.abaixo_do_custo.slice(0, 5);
  return (
    <div className="aviso aviso-dado">
      <strong>
        {total === 1 ? "1 item vendido abaixo do custo" : `${total} itens vendidos abaixo do custo`}{" "}
        em {mesAno(resumo.periodo)}: {reaisInteiro(prejuizo)} no mês.
      </strong>{" "}
      {mostrados.map((i, n) => (
        <span key={i.nome}>
          {n > 0 && "; "}
          {i.nome} ({reais(i.margem_unitaria)} por unidade × {num(i.quantidade)} ={" "}
          {reaisInteiro(i.margem_total)})
        </span>
      ))}
      {total > mostrados.length && `; e mais ${total - mostrados.length}`}. Confira a ficha
      técnica e o preço de venda.
    </div>
  );
}

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
  const [categoria, setCategoria] = useState<string | null>(null);
  const [itens, setItens] = useState<ItemEngenharia[]>([]);
  const [quadrante, setQuadrante] = useState<ClasseCardapio>("burro_de_carga");
  // Resultado e erro valem para a casa e o mês do cálculo, como nas outras telas.
  const [calculadoPara, setCalculadoPara] = useState("");
  const atual = calculadoPara === `${casaId}|${periodo}`;
  const erro = atual ? erroCalculado : null;
  const resumo = atual ? resumoCalculado : null;

  async function carregar(id: number, nome: string, cat: string | null) {
    setGrupo(nome);
    setCategoria(cat);
    setItens([]);
    try {
      setItens((await api.engenhariaCardapio(id, periodo, nome, cat, POR_PAGINA, 0)).items);
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
      if (dados.grupos.length > 0) {
        const primeiro = dados.grupos[0];
        await carregar(casaId, primeiro.grupo, primeiro.categoria ?? null);
      }
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível calcular a engenharia.");
    } finally {
      setCarregando(false);
    }
  }

  const doGrupo = resumo?.grupos.find(
    (g) => g.grupo === grupo && (g.categoria ?? null) === categoria,
  );
  const nomesGrupos = [...new Set(resumo?.grupos.map((g) => g.grupo) ?? [])];
  const rotulo = categoria ? `${grupo} · ${categoria}` : grupo;
  const doQuadrante = itens.filter((i) => i.classe === quadrante);

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Engenharia de cardápio</h2>
        <p className="ajuda">
          Cada item do mês no seu quadrante: quanto vende e quanto deixa de margem por unidade,
          comparado com os outros itens da mesma categoria. Cada quadrante tem uma ação.
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
            <AlertaAbaixoDoCusto resumo={resumo} />
          )}

          {/* Categorias de cardápio, por grupo: o método compara itens que
              competem entre si (chopp com chopp, petisco com petisco). */}
          <div className="categorias glass" role="radiogroup" aria-label="Categoria de cardápio">
            {nomesGrupos.map((nomeGrupo) => {
              const doNome = resumo.grupos.filter((g) => g.grupo === nomeGrupo);
              const fora = doNome[0]?.fora_da_matriz ?? 0;
              return (
                <div key={nomeGrupo} className="categorias-grupo">
                  <span className="categorias-titulo">
                    {nomeGrupo}
                    {fora > 0 && (
                      <span className="celula-fraca">{fora} itens fora (venda abaixo de R$ 500)</span>
                    )}
                  </span>
                  <span className="categorias-lista">
                    {doNome.map((g) => {
                      const ativa = g.grupo === grupo && (g.categoria ?? null) === categoria;
                      return (
                        <button
                          key={`${g.grupo}|${g.categoria}`}
                          type="button"
                          role="radio"
                          aria-checked={ativa}
                          className={ativa ? "chip-categoria chip-categoria-ativa" : "chip-categoria"}
                          onClick={() =>
                            casaId !== "" && carregar(casaId, g.grupo, g.categoria ?? null)
                          }
                        >
                          {g.categoria ?? g.grupo} <span>{g.itens}</span>
                        </button>
                      );
                    })}
                  </span>
                </div>
              );
            })}
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
                {QUADRANTES[quadrante].titulo} · {rotulo} · {doQuadrante.length}{" "}
                {doQuadrante.length === 1 ? "item" : "itens"}
              </h3>
              {doQuadrante.length === 0 ? (
                <p className="vazio">Nenhum item desta categoria neste quadrante.</p>
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
                            {item.popularidade_pct === null ? "" : `${pct(item.popularidade_pct)} da categoria`}
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
                <strong>Como lemos:</strong> {resumo.metodo} Em {rotulo}: margem média de{" "}
                {reais(doGrupo.margem_media_unitaria)} por unidade; popular = pelo menos{" "}
                {pct(doGrupo.limiar_popularidade_pct)} das unidades da categoria. {resumo.aviso}
              </p>
            </>
          )}
        </>
      )}
    </section>
  );
}
