import { useState } from "react";
import type { Casa } from "./api";
import { Casas } from "./screens/Casas";
import { Upload } from "./screens/Upload";
import { FecharMes } from "./screens/FecharMes";
import { Fechamento } from "./screens/Fechamento";
import { MargemItens } from "./screens/MargemItens";
import { Engenharia } from "./screens/Engenharia";
import "./App.css";

type Tela = "casas" | "upload" | "fecharmes" | "fechamento" | "margem" | "engenharia";

// A ordem é o fluxo real de uso: cadastra a casa, sobe o export, confere o
// fechamento e, item a item, decide o que mexer no cardápio.
//
// "Fechar o mês" (RF12) é o caminho guiado para quem está fechando pela
// primeira vez; "Upload" continua como está para quem já sabe o que precisa
// enviar. Trocar um pelo outro quebraria o fluxo de quem já usa.
//
// "Margem por item" vem depois do Fechamento: o fechamento diz QUE um grupo
// saiu do previsto, a margem por item diz QUAL item e quanto custou em reais.
// "Engenharia de cardápio" (RF16) fecha a sequência: onde cada item está hoje
// (popularidade × margem) e a ação de cada quadrante. Substituiu "Quanto
// comprar" (RF07) em 18/11 — a previsão não acertava mais que repetir o mês
// passado (docs/01-requisitos.md). A rota da API continua, fora do menu.
const TELAS: { id: Tela; rotulo: string }[] = [
  { id: "casas", rotulo: "Casas" },
  { id: "upload", rotulo: "Upload" },
  { id: "fecharmes", rotulo: "Fechar o mês" },
  { id: "fechamento", rotulo: "Fechamento" },
  { id: "margem", rotulo: "Margem por item" },
  { id: "engenharia", rotulo: "Engenharia de cardápio" },
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
        {tela === "fecharmes" && (
          <FecharMes
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
        {tela === "margem" && (
          <MargemItens
            casas={casas}
            casaId={casaId}
            setCasaId={setCasaId}
            periodo={periodo}
            setPeriodo={setPeriodo}
          />
        )}
        {tela === "engenharia" && (
          <Engenharia
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
