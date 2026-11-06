import { useEffect, useState } from "react";
import { api, ApiError, type Casa } from "../api";

export function Casas({ onCasasCarregadas }: { onCasasCarregadas?: (casas: Casa[]) => void }) {
  const [casas, setCasas] = useState<Casa[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);

  const [nome, setNome] = useState("");
  const [marca, setMarca] = useState("");
  const [cidade, setCidade] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erroForm, setErroForm] = useState<string | null>(null);

  async function carregar() {
    setCarregando(true);
    setErro(null);
    try {
      const pagina = await api.listarCasas();
      setCasas(pagina.items);
      onCasasCarregadas?.(pagina.items);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível carregar as casas.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function criar(ev: React.FormEvent) {
    ev.preventDefault();
    setEnviando(true);
    setErroForm(null);
    try {
      await api.criarCasa({ nome, marca, cidade, ativa: true });
      setNome("");
      setMarca("");
      setCidade("");
      setMostrarForm(false);
      await carregar();
    } catch (e) {
      setErroForm(e instanceof ApiError ? e.message : "Não foi possível criar a casa.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section>
      <header className="secao-cabecalho">
        <h2>Casas</h2>
        <button onClick={() => setMostrarForm((v) => !v)}>
          {mostrarForm ? "Cancelar" : "Nova casa"}
        </button>
      </header>

      {mostrarForm && (
        <form className="form-casa" onSubmit={criar}>
          <label>
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} required minLength={3} />
          </label>
          <label>
            Marca
            <input value={marca} onChange={(e) => setMarca(e.target.value)} required minLength={2} />
          </label>
          <label>
            Cidade
            <input value={cidade} onChange={(e) => setCidade(e.target.value)} required minLength={2} />
          </label>
          {erroForm && <p className="erro">{erroForm}</p>}
          <button type="submit" disabled={enviando}>
            {enviando ? "Criando…" : "Criar casa"}
          </button>
        </form>
      )}

      {carregando && <p>Carregando…</p>}
      {erro && <p className="erro">{erro}</p>}

      {!carregando && !erro && casas.length === 0 && (
        <p className="vazio">Nenhuma casa cadastrada ainda.</p>
      )}

      {!carregando && casas.length > 0 && (
        <table className="tabela">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Marca</th>
              <th>Cidade</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {casas.map((casa) => (
              <tr key={casa.id}>
                <td>{casa.nome}</td>
                <td>{casa.marca}</td>
                <td>{casa.cidade}</td>
                <td>
                  <span className={casa.ativa ? "chip chip-ok" : "chip chip-inativa"}>
                    {casa.ativa ? "Ativa" : "Inativa"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
