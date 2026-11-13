import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  type Casa,
  type DemoFechamento,
  type Fechamento as FechamentoDto,
  type TipoUpload,
  type UploadCusto,
  type UploadFechamento,
} from "../api";
import { PainelFechamento } from "./Fechamento";

/** Fluxo guiado "Fechar o mês" — RF12 (docs/11, seção 5).
 *
 * A aba Upload continua existindo e inalterada: quem já sabe o que está
 * fazendo manda os dois arquivos direto. Este fluxo é para quem está fechando
 * o mês pela primeira vez e não sabe que precisa dos **dois** lados — o erro
 * silencioso mais caro do contrato de entrada.
 *
 * Reenvio SUBSTITUI o upload anterior (restrição única de casa + período +
 * tipo). Por isso, quando já existe arquivo do passo, o padrão é "usar o já
 * enviado": substituir exige um clique explícito. Numa demo ao vivo, apontar
 * para a casa piloto no mês real e seguir o fluxo sobrescreveria o dado.
 */

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

type Coluna = { nome: string; regra: string };

// Tabela C de `docs/07-fechamento-cmv.md`, por lado do fechamento. Está na
// tela porque é o contrato de entrada: o que não estiver aqui o sistema não lê.
const LADOS: Record<
  TipoUpload,
  { titulo: string; subtitulo: string; relatorio: string; colunas: Coluna[] }
> = {
  cardapio: {
    titulo: "Lado teórico",
    subtitulo: "O que as fichas técnicas previam que o mês custaria",
    relatorio: "No Everest: engenharia de cardápio.",
    colunas: [
      { nome: "grupo", regra: "Obrigatória" },
      { nome: "custo", regra: "Obrigatória" },
      { nome: "venda_liquida", regra: "Sem ela não há CMV %" },
      { nome: "subgrupo", regra: "Opcional — detalha a explicação" },
      { nome: "item + quantidade", regra: "Opcional; necessária para \"Quanto comprar\"" },
    ],
  },
  compras: {
    titulo: "Lado real",
    subtitulo: "O que o mês custou de fato, depois do inventário de fim de mês",
    relatorio: "No Everest: DRE gerencial de compras.",
    colunas: [
      { nome: "grupo", regra: "Obrigatória" },
      { nome: "custo", regra: "Obrigatória" },
      { nome: "subgrupo", regra: "Opcional — detalha a explicação" },
      { nome: "venda_liquida", regra: "Opcional; usada só se faltar o lado teórico" },
    ],
  },
};

// Dois jeitos de fechar (12/11/2026): os dois relatórios do Everest, ou a
// planilha de fechamento, que traz os dois lados e o estoque num arquivo só.
type Modo = "everest" | "planilha";

const PASSOS: Record<Modo, string[]> = {
  everest: ["Casa e período", "Lado teórico", "Lado real", "Resultado"],
  planilha: ["Casa e período", "Planilha de fechamento", "Resultado"],
};

const COLUNAS_PLANILHA: Coluna[] = [
  { nome: "periodo", regra: "Obrigatória — AAAA-MM; o arquivo pode trazer vários meses" },
  { nome: "grupo", regra: "Obrigatória — só custo direto (ALIMENTOS, BEBIDAS…)" },
  { nome: "venda_liquida", regra: "Obrigatória" },
  { nome: "custo_teorico", regra: "Opcional; sem ela não há ajuste" },
  { nome: "estoque_inicial", regra: "Só no 1º mês; depois vem do estoque final anterior" },
  { nome: "compras", regra: "Obrigatória — líquidas de devoluções" },
  { nome: "estoque_final", regra: "Obrigatória — inventário do último dia do mês" },
];

const mesAno = (periodo: string) => {
  const [ano, mes] = periodo.split("-");
  return `${mes}/${ano.slice(2)}`;
};

function Passos({ rotulos, atual }: { rotulos: string[]; atual: number }) {
  return (
    <ol className="passos">
      {rotulos.map((rotulo, i) => (
        <li
          key={rotulo}
          className={i === atual ? "passo passo-ativo" : i < atual ? "passo passo-feito" : "passo"}
          aria-current={i === atual ? "step" : undefined}
        >
          <span className="passo-num">{i + 1}</span>
          {rotulo}
        </li>
      ))}
    </ol>
  );
}

function PassoEnvio({
  tipo,
  casaId,
  periodo,
  existente,
  onPronto,
  onComecouEnvio,
}: {
  tipo: TipoUpload;
  casaId: number;
  periodo: string;
  existente: UploadCusto | undefined;
  onPronto: (enviou: boolean) => void;
  /** Chamado no instante em que o arquivo sai, antes da resposta — é daqui
   * que o cronômetro do RF13 conta. */
  onComecouEnvio: () => void;
}) {
  const lado = LADOS[tipo];
  const [substituir, setSubstituir] = useState(false);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // O estado volta ao padrão "usar o já enviado" a cada passo porque quem
  // monta passa uma `key` por (tipo, casa, período): o componente é remontado,
  // em vez de um efeito que reseta estado depois de renderizar o anterior.
  const mostrarEnvio = existente === undefined || substituir;

  async function enviar() {
    if (!arquivo) return;
    setEnviando(true);
    setErro(null);
    onComecouEnvio();
    try {
      await api.enviarUpload({ casa_id: casaId, periodo, tipo, arquivo });
      onPronto(true);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="glass passo-painel">
      <h3>{lado.titulo}</h3>
      <p className="ajuda">{lado.subtitulo}</p>

      <table className="tabela tabela-colunas">
        <thead>
          <tr>
            <th>Coluna</th>
            <th>Regra</th>
          </tr>
        </thead>
        <tbody>
          {lado.colunas.map((c) => (
            <tr key={c.nome}>
              <td>
                <code>{c.nome}</code>
              </td>
              <td>{c.regra}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="ajuda">
        {lado.relatorio} O export do Everest também é aceito como está — não precisa arrumar nada.
      </p>
      <a className="botao-secundario" href={api.urlModelo(tipo)} download>
        Baixar planilha-modelo
      </a>

      {existente !== undefined && !substituir && (
        <>
          <p className="ok">
            Já enviado em {new Date(existente.criado_em).toLocaleDateString("pt-BR")} —{" "}
            {existente.linhas_importadas} linhas.
          </p>
          <div className="passo-acoes">
            <button type="button" className="botao-primario" onClick={() => onPronto(false)}>
              Usar o já enviado
            </button>
            <button type="button" className="botao-secundario" onClick={() => setSubstituir(true)}>
              Enviar outro arquivo
            </button>
          </div>
        </>
      )}

      {existente !== undefined && substituir && (
        <p className="aviso aviso-substituicao">
          Enviar agora <strong>substitui</strong> o arquivo de{" "}
          {new Date(existente.criado_em).toLocaleDateString("pt-BR")} e as linhas dele. Não tem como
          desfazer.
        </p>
      )}

      {mostrarEnvio && (
        <>
          <label className="dropzone">
            <input
              type="file"
              accept=".xlsx"
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            />
            {arquivo ? (
              <span className="dropzone-arquivo">
                <strong>{arquivo.name}</strong>
                <span>{(arquivo.size / 1024).toFixed(0)} KB — pronto pra enviar</span>
              </span>
            ) : (
              <span className="dropzone-vazio">
                <strong>Escolha o .xlsx</strong>
                <span>export do Everest ou a planilha-modelo preenchida</span>
              </span>
            )}
          </label>
          {erro && <p className="erro">{erro}</p>}
          <div className="passo-acoes">
            <button
              type="button"
              className="botao-primario"
              disabled={!arquivo || enviando}
              onClick={enviar}
            >
              {enviando ? "Enviando…" : "Enviar e continuar"}
            </button>
            {existente !== undefined && (
              <button
                type="button"
                className="botao-secundario"
                onClick={() => setSubstituir(false)}
              >
                Cancelar
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function PassoPlanilha({
  casaId,
  periodo,
  existente,
  urlDemo,
  onPronto,
  onComecouEnvio,
}: {
  casaId: number;
  periodo: string;
  /** Envio da planilha que já traz este mês, se houver. */
  existente: UploadFechamento | undefined;
  /** Só para a casa de demonstração, e só se a demo tem este mês. */
  urlDemo: string | null;
  onPronto: () => void;
  onComecouEnvio: () => void;
}) {
  const [substituir, setSubstituir] = useState(false);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const mostrarEnvio = existente === undefined || substituir;

  async function enviar() {
    if (!arquivo) return;
    setEnviando(true);
    setErro(null);
    onComecouEnvio();
    try {
      const envio = await api.enviarPlanilhaFechamento({ casa_id: casaId, arquivo });
      // A planilha diz os próprios meses: se não trouxe o mês do fluxo, não
      // há resultado a mostrar — melhor dizer isso do que um 404 genérico.
      if (!envio.periodos.includes(periodo)) {
        setErro(
          `Planilha enviada, mas ela não traz ${mesAno(periodo)}: traz ` +
            `${envio.periodos.map(mesAno).join(", ")}. Escolha um desses meses ou envie ` +
            "outra planilha.",
        );
        return;
      }
      onPronto();
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar a planilha.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="glass passo-painel">
      <h3>Planilha de fechamento</h3>
      <p className="ajuda">
        Os dois lados e o estoque num arquivo só. Com o estoque, o lado real é o CMV real:
        estoque inicial + compras − estoque final.
      </p>

      <table className="tabela tabela-colunas">
        <thead>
          <tr>
            <th>Coluna</th>
            <th>Regra</th>
          </tr>
        </thead>
        <tbody>
          {COLUNAS_PLANILHA.map((c) => (
            <tr key={c.nome}>
              <td>
                <code>{c.nome}</code>
              </td>
              <td>{c.regra}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="passo-acoes">
        <a className="botao-secundario" href={api.urlModelo("fechamento")} download>
          Baixar planilha-modelo
        </a>
        {urlDemo && (
          <a className="botao-secundario" href={urlDemo} download>
            Baixar planilha da demonstração ({mesAno(periodo)}, dados fictícios)
          </a>
        )}
      </div>

      {existente !== undefined && !substituir && (
        <>
          <p className="ok">
            {mesAno(periodo)} já veio na planilha enviada em{" "}
            {new Date(existente.criado_em).toLocaleDateString("pt-BR")}.
          </p>
          <div className="passo-acoes">
            <button type="button" className="botao-primario" onClick={onPronto}>
              Usar o já enviado
            </button>
            <button type="button" className="botao-secundario" onClick={() => setSubstituir(true)}>
              Enviar outro arquivo
            </button>
          </div>
        </>
      )}

      {existente !== undefined && substituir && (
        <p className="aviso aviso-substituicao">
          Cada mês da planilha nova <strong>substitui</strong> o mesmo mês enviado antes, com
          todos os grupos. Não tem como desfazer.
        </p>
      )}

      {mostrarEnvio && (
        <>
          <label className="dropzone">
            <input
              type="file"
              accept=".xlsx"
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            />
            {arquivo ? (
              <span className="dropzone-arquivo">
                <strong>{arquivo.name}</strong>
                <span>{(arquivo.size / 1024).toFixed(0)} KB — pronto pra enviar</span>
              </span>
            ) : (
              <span className="dropzone-vazio">
                <strong>Escolha o .xlsx</strong>
                <span>a planilha de fechamento preenchida</span>
              </span>
            )}
          </label>
          {erro && <p className="erro">{erro}</p>}
          <div className="passo-acoes">
            <button
              type="button"
              className="botao-primario"
              disabled={!arquivo || enviando}
              onClick={enviar}
            >
              {enviando ? "Enviando…" : "Enviar e ver o resultado"}
            </button>
            {existente !== undefined && (
              <button
                type="button"
                className="botao-secundario"
                onClick={() => setSubstituir(false)}
              >
                Cancelar
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export function FecharMes({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [passo, setPasso] = useState(0);
  const [modo, setModo] = useState<Modo>("everest");
  const [uploads, setUploads] = useState<UploadCusto[]>([]);
  const [planilhas, setPlanilhas] = useState<UploadFechamento[]>([]);
  const [demo, setDemo] = useState<DemoFechamento | null>(null);
  const [fechamento, setFechamento] = useState<FechamentoDto | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);
  // RF13: tempo de relógio do primeiro envio deste fluxo até o resultado na
  // tela. Marcado só quando um arquivo é de fato enviado — quem reaproveita
  // os dois uploads não "fechou o mês" agora, e cronometrar isso seria
  // medir um clique. `null` enquanto nada foi enviado.
  const [inicio, setInicio] = useState<number | null>(null);
  const [segundos, setSegundos] = useState<number | null>(null);

  // Backend antigo não tem a rota: sem ela, simplesmente não há planilha de demo.
  useEffect(() => {
    api
      .demoFechamento()
      .then(setDemo)
      .catch(() => setDemo(null));
  }, []);

  async function recarregarUploads(id: number) {
    try {
      setUploads((await api.listarUploads(id)).items);
    } catch {
      setUploads([]);
    }
    try {
      setPlanilhas((await api.listarPlanilhasFechamento(id)).items);
    } catch {
      setPlanilhas([]);
    }
  }

  const planilhaDoPeriodo = planilhas.find((p) => p.periodos.includes(periodo));
  // A planilha de demonstração só aparece para a casa de demonstração, e só
  // para um mês que a demo tem: em outra casa, misturaria dado fictício com real.
  const urlDemo =
    demo !== null &&
    casas.some((c) => c.id === casaId && c.nome === demo.casa_nome) &&
    demo.periodos.includes(periodo)
      ? api.urlPlanilhaDemo(periodo)
      : null;

  const doPeriodo = (tipo: TipoUpload) =>
    uploads.find((u) => u.periodo === periodo && u.tipo === tipo);

  async function avancarDe(tipo: TipoUpload, enviou: boolean) {
    if (casaId === "") return;
    if (enviou) await recarregarUploads(casaId);
    if (tipo === "cardapio") {
      setPasso(2);
      return;
    }
    await calcular();
  }

  async function calcular() {
    if (casaId === "") return;
    setCalculando(true);
    setErro(null);
    try {
      setFechamento(await api.fechamento(casaId, periodo));
      if (inicio !== null) setSegundos((performance.now() - inicio) / 1000);
      setPasso(3);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível calcular o fechamento.");
    } finally {
      setCalculando(false);
    }
  }

  function recomecar() {
    setPasso(0);
    setFechamento(null);
    setErro(null);
    setInicio(null);
    setSegundos(null);
  }

  function marcarInicio() {
    setInicio((t) => t ?? performance.now());
  }

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Fechar o mês</h2>
        <p className="ajuda">
          Os dois relatórios e o resultado, em quatro passos. O fechamento precisa dos{" "}
          <strong>dois lados</strong>: só o teórico não produz ajuste nenhum.
        </p>
      </header>

      {/* O resultado é sempre o passo 3; no modo planilha ele é o 3º rótulo. */}
      <Passos rotulos={PASSOS[modo]} atual={modo === "planilha" && passo === 3 ? 2 : passo} />

      {passo === 0 && (
        <form
          className="glass form-fechamento"
          onSubmit={async (e) => {
            e.preventDefault();
            if (casaId === "" || !periodo) return;
            await recarregarUploads(casaId);
            setPasso(1);
          }}
        >
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
          <div className="campo">
            <span className="campo-rotulo">Como vai enviar</span>
            <div className="segmentado" role="radiogroup">
              <button
                type="button"
                role="radio"
                aria-checked={modo === "everest"}
                className={modo === "everest" ? "segmento segmento-ativo" : "segmento"}
                onClick={() => setModo("everest")}
              >
                <strong>Relatórios do Everest</strong>
                <span>dois arquivos: teórico e real</span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={modo === "planilha"}
                className={modo === "planilha" ? "segmento segmento-ativo" : "segmento"}
                onClick={() => setModo("planilha")}
              >
                <strong>Planilha de fechamento</strong>
                <span>um arquivo, com o estoque</span>
              </button>
            </div>
          </div>
          <button type="submit" className="botao-primario">
            Começar
          </button>
        </form>
      )}

      {passo === 1 && casaId !== "" && modo === "planilha" && (
        <PassoPlanilha
          key={`planilha-${casaId}-${periodo}`}
          casaId={casaId}
          periodo={periodo}
          existente={planilhaDoPeriodo}
          urlDemo={urlDemo}
          onPronto={calcular}
          onComecouEnvio={marcarInicio}
        />
      )}

      {passo === 1 && casaId !== "" && modo === "everest" && (
        <PassoEnvio
          key={`cardapio-${casaId}-${periodo}`}
          tipo="cardapio"
          casaId={casaId}
          periodo={periodo}
          existente={doPeriodo("cardapio")}
          onPronto={(enviou) => avancarDe("cardapio", enviou)}
          onComecouEnvio={marcarInicio}
        />
      )}

      {passo === 2 && casaId !== "" && (
        <PassoEnvio
          key={`compras-${casaId}-${periodo}`}
          tipo="compras"
          casaId={casaId}
          periodo={periodo}
          existente={doPeriodo("compras")}
          onPronto={(enviou) => avancarDe("compras", enviou)}
          onComecouEnvio={marcarInicio}
        />
      )}

      {calculando && <p className="ajuda">Calculando o fechamento…</p>}
      {erro && <p className="erro">{erro}</p>}

      {passo === 3 && fechamento && (
        <>
          {/* RF13. Os "2 dias" do processo manual são trabalho humano
              DECLARADO pelo cliente, nunca medido, e incluem exportar os
              relatórios do ERP. Comparar os dois números sem dizer isso seria
              um flanco aberto — por isso a ressalva anda junto do tempo. */}
          {segundos !== null && (
            <p className="cronometro glass">
              <strong>Do primeiro envio ao resultado: {segundos.toFixed(1)} s</strong>
              <span>
                Não inclui o tempo de exportar os relatórios do ERP. Hoje o fechamento manual
                leva cerca de dois dias por casa, segundo a equipe de custos — é um número
                declarado por eles, não medido por nós.
              </span>
            </p>
          )}
          <PainelFechamento dados={fechamento} />
          <button type="button" className="botao-secundario" onClick={recomecar}>
            Fechar outro mês
          </button>
        </>
      )}
    </section>
  );
}
