import { useState } from "react";
import type { Casa } from "./api";
import { Casas } from "./screens/Casas";
import { Upload } from "./screens/Upload";
import { Fechamento } from "./screens/Fechamento";
import "./App.css";

type Tela = "casas" | "upload" | "fechamento";

const TELAS: { id: Tela; rotulo: string }[] = [
  { id: "casas", rotulo: "Casas" },
  { id: "upload", rotulo: "Upload" },
  { id: "fechamento", rotulo: "Fechamento" },
];

export default function App() {
  const [tela, setTela] = useState<Tela>("casas");
  const [casas, setCasas] = useState<Casa[]>([]);
  // Casa e período ficam aqui, não dentro de cada tela: trocar de aba não deve
  // obrigar a escolher a casa de novo — é o mesmo fluxo da reunião de
  // fechamento, sobe o arquivo e confere o painel da mesma casa em seguida.
  const [casaId, setCasaId] = useState<number | "">("");
  const [periodo, setPeriodo] = useState("");

  return (
    <div className="app">
      <div className="ambient" aria-hidden="true" />
      <header className="app-cabecalho">
        <div className="marca">
          <span className="marca-ponto" />
          Grupo Saints <span className="marca-fraco">· Fechamento de CMV</span>
        </div>
        <nav className="abas" aria-label="Navegação principal">
          {TELAS.map((t) => (
            <button
              key={t.id}
              className={tela === t.id ? "aba aba-ativa" : "aba"}
              onClick={() => setTela(t.id)}
            >
              {t.rotulo}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-conteudo">
        {tela === "casas" && <Casas onCasasCarregadas={setCasas} />}
        {tela === "upload" && (
          <Upload
            casas={casas}
            casaId={casaId}
            setCasaId={setCasaId}
            periodo={periodo}
            setPeriodo={setPeriodo}
          />
        )}
        {tela === "fechamento" && (
          <Fechamento
            casas={casas}
            casaId={casaId}
            setCasaId={setCasaId}
            periodo={periodo}
            setPeriodo={setPeriodo}
          />
        )}
      </main>
    </div>
  );
}
