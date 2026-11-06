import { useState } from "react";
import type { Casa } from "./api";
import { Casas } from "./screens/Casas";
import { Upload } from "./screens/Upload";
import { Fechamento } from "./screens/Fechamento";
import "./App.css";

type Tela = "casas" | "upload" | "fechamento";

export default function App() {
  const [tela, setTela] = useState<Tela>("casas");
  const [casas, setCasas] = useState<Casa[]>([]);

  return (
    <div className="app">
      <header className="app-cabecalho">
        <h1>Grupo Saints — Fechamento de CMV</h1>
        <nav className="abas">
          <button className={tela === "casas" ? "aba aba-ativa" : "aba"} onClick={() => setTela("casas")}>
            Casas
          </button>
          <button className={tela === "upload" ? "aba aba-ativa" : "aba"} onClick={() => setTela("upload")}>
            Upload
          </button>
          <button
            className={tela === "fechamento" ? "aba aba-ativa" : "aba"}
            onClick={() => setTela("fechamento")}
          >
            Fechamento
          </button>
        </nav>
      </header>

      <main className="app-conteudo">
        {tela === "casas" && <Casas onCasasCarregadas={setCasas} />}
        {tela === "upload" && <Upload casas={casas} />}
        {tela === "fechamento" && <Fechamento casas={casas} />}
      </main>
    </div>
  );
}
