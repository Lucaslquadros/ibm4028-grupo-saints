import { useRef, useState } from "react";
import { api, ApiError, type Casa, type TipoUpload, type UploadCusto } from "../api";

const PERIODO_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export function Upload({ casas }: { casas: Casa[] }) {
  const [casaId, setCasaId] = useState<number | "">("");
  const [periodo, setPeriodo] = useState("");
  const [tipo, setTipo] = useState<TipoUpload>("cardapio");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<UploadCusto | null>(null);
  const inputArquivoRef = useRef<HTMLInputElement>(null);

  const podeEnviar =
    casaId !== "" && PERIODO_PATTERN.test(periodo) && arquivo !== null && !enviando;

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
    <section>
      <h2>Upload de export do Everest</h2>
      <p className="ajuda">
        Envie o export como sai do Everest, em .xlsx. Reenviar o mesmo casa/período/tipo
        substitui o anterior.
      </p>

      <form className="form-upload" onSubmit={enviar}>
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

        <label>
          Tipo de relatório
          <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoUpload)}>
            <option value="cardapio">Engenharia de cardápio (CMV teórico)</option>
            <option value="compras">DRE de compras (CMV real)</option>
          </select>
        </label>

        <label>
          Arquivo (.xlsx)
          <input
            ref={inputArquivoRef}
            type="file"
            accept=".xlsx"
            onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            required
          />
        </label>

        {erro && <p className="erro">{erro}</p>}
        {resultado && (
          <p className="ok">
            Enviado: {resultado.linhas_importadas} linhas importadas
            {resultado.substituiu_anterior ? " (substituiu o upload anterior)" : ""}.
          </p>
        )}

        <button type="submit" disabled={!podeEnviar}>
          {enviando ? "Enviando…" : "Enviar"}
        </button>
      </form>
    </section>
  );
}
