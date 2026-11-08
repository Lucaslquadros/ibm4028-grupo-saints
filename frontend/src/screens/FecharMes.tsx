import { useState } from "react";
import {
  api,
  ApiError,
  type Casa,
  type Fechamento as FechamentoDto,
  type TipoUpload,
  type UploadCusto,
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

const PASSOS = ["Casa e período", "Lado teórico", "Lado real", "Resultado"];

function Passos({ atual }: { atual: number }) {
  return (
    <ol className="passos">
      {PASSOS.map((rotulo, i) => (
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
}: {
  tipo: TipoUpload;
  casaId: number;
  periodo: string;
  existente: UploadCusto | undefined;
  onPronto: (enviou: boolean) => void;
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

export function FecharMes({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [passo, setPasso] = useState(0);
  const [uploads, setUploads] = useState<UploadCusto[]>([]);
  const [fechamento, setFechamento] = useState<FechamentoDto | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);

  async function recarregarUploads(id: number) {
    try {
      setUploads((await api.listarUploads(id)).items);
    } catch {
      setUploads([]);
    }
  }

  const doPeriodo = (tipo: TipoUpload) =>
    uploads.find((u) => u.periodo === periodo && u.tipo === tipo);

  async function avancarDe(tipo: TipoUpload, enviou: boolean) {
    if (casaId === "") return;
    if (enviou) await recarregarUploads(casaId);
    if (tipo === "cardapio") {
      setPasso(2);
      return;
    }
    setCalculando(true);
    setErro(null);
    try {
      setFechamento(await api.fechamento(casaId, periodo));
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

      <Passos atual={passo} />

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
          <button type="submit" className="botao-primario">
            Começar
          </button>
        </form>
      )}

      {passo === 1 && casaId !== "" && (
        <PassoEnvio
          key={`cardapio-${casaId}-${periodo}`}
          tipo="cardapio"
          casaId={casaId}
          periodo={periodo}
          existente={doPeriodo("cardapio")}
          onPronto={(enviou) => avancarDe("cardapio", enviou)}
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
        />
      )}

      {calculando && <p className="ajuda">Calculando o fechamento…</p>}
      {erro && <p className="erro">{erro}</p>}

      {passo === 3 && fechamento && (
        <>
          <PainelFechamento dados={fechamento} />
          <button type="button" className="botao-secundario" onClick={recomecar}>
            Fechar outro mês
          </button>
        </>
      )}
    </section>
  );
}
