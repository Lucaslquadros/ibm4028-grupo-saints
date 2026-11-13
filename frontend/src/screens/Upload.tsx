import { useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Casa,
  type TipoUpload,
  type UploadCusto,
  type UploadFechamento,
} from "../api";

// "fechamento" é a planilha-modelo (12/11/2026): um arquivo com os dois lados
// e o estoque, de um ou vários meses. O período vem no arquivo, não no form.
type Modo = TipoUpload | "fechamento";

const RECEITAS: Record<Modo, { rotulo: string; detalhe: string }> = {
  cardapio: { rotulo: "Engenharia de cardápio", detalhe: "CMV teórico" },
  compras: { rotulo: "DRE de compras", detalhe: "compras do mês, sem estoque" },
  fechamento: { rotulo: "Planilha de fechamento", detalhe: "teórico + CMV real com estoque" },
};

const mesAno = (periodo: string) => {
  const [ano, mes] = periodo.split("-");
  return `${mes}/${ano.slice(2)}`;
};

const intervalo = (periodos: string[]) =>
  periodos.length === 0
    ? "nenhum mês"
    : periodos.length === 1
      ? mesAno(periodos[0])
      : `${mesAno(periodos[0])} a ${mesAno(periodos[periodos.length - 1])}`;

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function Upload({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [tipo, setTipo] = useState<Modo>("cardapio");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<UploadCusto | null>(null);
  const [resultadoPlanilha, setResultadoPlanilha] = useState<UploadFechamento | null>(null);
  const [uploadsCasa, setUploadsCasa] = useState<UploadCusto[]>([]);
  const [planilhasCasa, setPlanilhasCasa] = useState<UploadFechamento[]>([]);
  const inputArquivoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (casaId === "") return;
    api
      .listarUploads(casaId)
      .then((p) => setUploadsCasa(p.items))
      .catch(() => setUploadsCasa([]));
    api
      .listarPlanilhasFechamento(casaId)
      .then((p) => setPlanilhasCasa(p.items))
      .catch(() => setPlanilhasCasa([]));
  }, [casaId, resultado, resultadoPlanilha]);

  const ehPlanilha = tipo === "fechamento";
  const existente =
    casaId !== "" &&
    !ehPlanilha &&
    uploadsCasa.find((u) => u.periodo === periodo && u.tipo === tipo);
  const mesesComPlanilha = [...new Set(planilhasCasa.flatMap((p) => p.periodos))].sort();
  const podeEnviar =
    casaId !== "" && (ehPlanilha || periodo !== "") && arquivo !== null && !enviando;

  function escolherArquivo(f: File | null) {
    setArquivo(f);
    setResultado(null);
    setResultadoPlanilha(null);
  }

  async function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!podeEnviar) return;
    setEnviando(true);
    setErro(null);
    setResultado(null);
    setResultadoPlanilha(null);
    try {
      if (tipo === "fechamento") {
        setResultadoPlanilha(
          await api.enviarPlanilhaFechamento({ casa_id: casaId, arquivo }),
        );
      } else {
        setResultado(await api.enviarUpload({ casa_id: casaId, periodo, tipo, arquivo }));
      }
      setArquivo(null);
      if (inputArquivoRef.current) inputArquivoRef.current.value = "";
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="tela">
      <header className="tela-cabecalho">
        <h2>Upload</h2>
        <p className="ajuda">
          Envie o export como sai do Everest, ou a planilha de fechamento preenchida — sempre em
          .xlsx.
        </p>
      </header>

      <form className="glass form-upload" onSubmit={enviar}>
        <div className="campo-grid">
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

          {!ehPlanilha && (
            <label className="campo">
              <span className="campo-rotulo">Período</span>
              <input
                type="month"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                required
              />
            </label>
          )}
        </div>

        <div className="campo">
          <span className="campo-rotulo">Tipo de relatório</span>
          <div className="segmentado" role="radiogroup">
            {(Object.keys(RECEITAS) as Modo[]).map((k) => (
              <button
                type="button"
                key={k}
                role="radio"
                aria-checked={tipo === k}
                className={tipo === k ? "segmento segmento-ativo" : "segmento"}
                onClick={() => setTipo(k)}
              >
                <strong>{RECEITAS[k].rotulo}</strong>
                <span>{RECEITAS[k].detalhe}</span>
              </button>
            ))}
          </div>
        </div>

        {ehPlanilha && (
          <div className="ajuda">
            <p>
              Uma linha por grupo por mês, com venda, custo teórico, compras e o estoque do
              inventário. O mês vem na planilha: um envio pode trazer um mês ou o histórico
              inteiro. Reenviar um mês substitui esse mês por inteiro.
            </p>
            <a className="botao-secundario" href={api.urlModelo("fechamento")} download>
              Baixar planilha-modelo
            </a>
            {casaId !== "" && mesesComPlanilha.length > 0 && (
              <p>
                Esta casa já tem {mesesComPlanilha.length}{" "}
                {mesesComPlanilha.length === 1 ? "mês" : "meses"} pela planilha (
                {intervalo(mesesComPlanilha)}).
              </p>
            )}
          </div>
        )}

        {existente && (
          <p className="aviso aviso-substituicao">
            Já existe um upload de <strong>{RECEITAS[tipo].rotulo.toLowerCase()}</strong> para este
            período, enviado em{" "}
            {new Date(existente.criado_em).toLocaleDateString("pt-BR")} ({existente.linhas_importadas}{" "}
            linhas). Enviar agora vai <strong>substituir</strong> esse upload.
          </p>
        )}

        <label
          className={arrastando ? "dropzone dropzone-ativa" : "dropzone"}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastando(true);
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastando(false);
            const f = e.dataTransfer.files?.[0];
            if (f) escolherArquivo(f);
          }}
        >
          <input
            ref={inputArquivoRef}
            type="file"
            accept=".xlsx"
            onChange={(e) => escolherArquivo(e.target.files?.[0] ?? null)}
            required
          />
          {arquivo ? (
            <span className="dropzone-arquivo">
              <strong>{arquivo.name}</strong>
              <span>{(arquivo.size / 1024).toFixed(0)} KB — pronto pra enviar</span>
            </span>
          ) : (
            <span className="dropzone-vazio">
              <strong>Arraste o .xlsx aqui</strong>
              <span>ou clique pra escolher o arquivo</span>
            </span>
          )}
        </label>

        {erro && <p className="erro">{erro}</p>}
        {resultadoPlanilha && (
          <p className="ok">
            Enviado: {resultadoPlanilha.linhas_importadas} linhas de{" "}
            {resultadoPlanilha.periodos.length}{" "}
            {resultadoPlanilha.periodos.length === 1 ? "mês" : "meses"} (
            {intervalo(resultadoPlanilha.periodos)})
            {resultadoPlanilha.meses_substituidos.length > 0
              ? `; substituiu ${resultadoPlanilha.meses_substituidos.map(mesAno).join(", ")}`
              : ""}
            .
          </p>
        )}
        {resultado && (
          <p className="ok">
            Enviado: {resultado.linhas_importadas} linhas importadas
            {resultado.substituiu_anterior ? " (substituiu o upload anterior)" : ""}.
          </p>
        )}

        <button type="submit" className="botao-primario" disabled={!podeEnviar}>
          {enviando ? "Enviando…" : ehPlanilha ? "Enviar planilha" : "Enviar export"}
        </button>
      </form>
    </section>
  );
}
