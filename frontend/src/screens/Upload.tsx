import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Casa, type TipoUpload, type UploadCusto } from "../api";

const RECEITAS: Record<TipoUpload, { rotulo: string; detalhe: string }> = {
  cardapio: { rotulo: "Engenharia de cardápio", detalhe: "CMV teórico" },
  compras: { rotulo: "DRE de compras", detalhe: "CMV real" },
};

type Props = {
  casas: Casa[];
  casaId: number | "";
  setCasaId: (v: number | "") => void;
  periodo: string;
  setPeriodo: (v: string) => void;
};

export function Upload({ casas, casaId, setCasaId, periodo, setPeriodo }: Props) {
  const [tipo, setTipo] = useState<TipoUpload>("cardapio");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<UploadCusto | null>(null);
  const [uploadsCasa, setUploadsCasa] = useState<UploadCusto[]>([]);
  const inputArquivoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (casaId === "") return;
    api
      .listarUploads(casaId)
      .then((p) => setUploadsCasa(p.items))
      .catch(() => setUploadsCasa([]));
  }, [casaId, resultado]);

  const existente =
    casaId !== "" && uploadsCasa.find((u) => u.periodo === periodo && u.tipo === tipo);
  const podeEnviar = casaId !== "" && periodo !== "" && arquivo !== null && !enviando;

  function escolherArquivo(f: File | null) {
    setArquivo(f);
    setResultado(null);
  }

  async function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!podeEnviar) return;
    setEnviando(true);
    setErro(null);
    setResultado(null);
    try {
      const upload = await api.enviarUpload({ casa_id: casaId, periodo, tipo, arquivo });
      setResultado(upload);
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
        <h2>Upload de export do Everest</h2>
        <p className="ajuda">Envie o export como sai do Everest, em .xlsx — sem precisar arrumar nada.</p>
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

          <label className="campo">
            <span className="campo-rotulo">Período</span>
            <input
              type="month"
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
              required
            />
          </label>
        </div>

        <div className="campo">
          <span className="campo-rotulo">Tipo de relatório</span>
          <div className="segmentado" role="radiogroup">
            {(Object.keys(RECEITAS) as TipoUpload[]).map((k) => (
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
        {resultado && (
          <p className="ok">
            Enviado: {resultado.linhas_importadas} linhas importadas
            {resultado.substituiu_anterior ? " (substituiu o upload anterior)" : ""}.
          </p>
        )}

        <button type="submit" className="botao-primario" disabled={!podeEnviar}>
          {enviando ? "Enviando…" : "Enviar export"}
        </button>
      </form>
    </section>
  );
}
