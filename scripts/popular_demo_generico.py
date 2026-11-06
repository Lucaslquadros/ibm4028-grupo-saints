"""Carrega a unidade de demonstração de **outro segmento**, pela API.

    # local (API subida com `uv run fastapi dev app/main.py`)
    uv run python scripts/popular_demo_generico.py

    # produção
    uv run python scripts/popular_demo_generico.py \
        --api https://app-projeto4-saints2026.azurewebsites.net

    # só gerar as planilhas, para anexar numa apresentação ou enviar a alguém
    uv run python scripts/popular_demo_generico.py --apenas-planilhas pasta/

Para que serve
--------------
O sistema nasceu lendo dois relatórios do Everest de um grupo de bares. A
afirmação de que ele resolve o fechamento manual de **qualquer** negócio só vale
se existir dado de um negócio que não é esse. Este script cria esse dado:

  - uma unidade de outro segmento (farmácia), com 6 meses de histórico;
  - as duas pontas do fechamento em **planilha genérica**, não em export do
    Everest — exercitando `leitores.ler_planilha`;
  - um grupo (EMBALAGENS) que só existe no lado real, para mostrar
    `crud.grupos_comparaveis` excluindo custo indireto sem lista hardcoded.

Vai pela API de propósito (e não direto no banco, como
`scripts/importar_exports.py`): assim o `POST /api/v1/uploads-custo` é exercido
de verdade, com validação, Blob e tudo o que roda em produção.

Dado inventado, e rotulado como tal
-----------------------------------
Os números NÃO são do cliente. O nome da unidade carrega "(DEMO)" para que
ninguém confunda isto com a casa piloto real em nenhuma tela ou slide.
"""

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# O console do Windows abre em cp1252, que não tem "→" nem "ç": sem isto o
# script morre num UnicodeEncodeError no print, depois de já ter gravado o dado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from openpyxl import Workbook  # noqa: E402

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


def carregar_catalogo() -> tuple[list[tuple[str, float]], list[dict]]:
    """Lê `exemplos/`: (meses, empresas). Nada de dado embutido no script.

    O dado fica em CSV versionado em vez de .xlsx porque o `.gitignore` bloqueia
    `*.xlsx` para planilha de cliente nunca entrar no Git — abrir exceção criaria
    um furo nessa proteção. O .xlsx é gerado aqui, na hora.
    """
    manifesto = json.loads((EXEMPLOS / "empresas.json").read_text(encoding="utf-8"))
    meses = [(m["periodo"], m["fator_real"]) for m in manifesto["meses"]]

    empresas = []
    for e in manifesto["empresas"]:
        empresas.append(
            {
                **e,
                "teorico": _ler_csv(EXEMPLOS / f"{e['slug']}-teorico.csv"),
                "real": _ler_csv(EXEMPLOS / f"{e['slug']}-real.csv"),
            }
        )
    return meses, empresas


def _ler_csv(caminho: Path) -> tuple[list[str], list[list]]:
    """(títulos, linhas). Números viram float; o resto fica texto."""
    with caminho.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.reader(f))
    if not linhas:
        raise SystemExit(f"{caminho.name} está vazio")
    titulos, corpo = linhas[0], []
    for linha in linhas[1:]:
        if not any(c.strip() for c in linha):
            continue
        corpo.append([_talvez_numero(c) for c in linha])
    return titulos, corpo


def _talvez_numero(valor: str):
    try:
        return float(valor)
    except ValueError:
        return valor


def _escalar_custo(titulos: list[str], linhas: list[list], fator: float) -> list[list]:
    """Multiplica só a coluna de custo. O fator move o custo REAL sem mover a
    venda, para o ajuste variar mês a mês e o gráfico ter forma, não uma reta."""
    try:
        idx = [t.strip().lower() for t in titulos].index("custo")
    except ValueError as exc:
        raise SystemExit(f"CSV sem coluna 'custo': {titulos}") from exc

    escaladas = []
    for linha in linhas:
        copia = list(linha)
        if isinstance(copia[idx], float):
            copia[idx] = round(copia[idx] * fator, 2)
        escaladas.append(copia)
    return escaladas


def _xlsx(titulos: list[str], linhas: list[list]) -> bytes:
    livro = Workbook()
    aba = livro.active
    aba.title = "Dados"
    aba.append(titulos)
    for linha in linhas:
        aba.append(linha)
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------ cliente HTTP
def _requisicao(url: str, dados: bytes | None, tipo: str | None, metodo: str) -> dict:
    req = urllib.request.Request(url, data=dados, method=metodo)
    if tipo:
        req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, timeout=120) as resposta:
            corpo = resposta.read().decode()
            return {"status": resposta.status, "corpo": corpo}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "corpo": exc.read().decode(errors="replace")}


def _multipart(campos: dict[str, str], nome_arquivo: str, conteudo: bytes) -> tuple[bytes, str]:
    """Monta o corpo multipart à mão para não precisar de `requests` só por isto."""
    limite = f"----demo{uuid.uuid4().hex}"
    partes = bytearray()
    for chave, valor in campos.items():
        partes += f"--{limite}\r\n".encode()
        partes += f'Content-Disposition: form-data; name="{chave}"\r\n\r\n'.encode()
        partes += f"{valor}\r\n".encode()
    partes += f"--{limite}\r\n".encode()
    partes += (
        f'Content-Disposition: form-data; name="arquivo"; filename="{nome_arquivo}"\r\n'
    ).encode()
    partes += f"Content-Type: {XLSX}\r\n\r\n".encode()
    partes += conteudo + b"\r\n"
    partes += f"--{limite}--\r\n".encode()
    return bytes(partes), f"multipart/form-data; boundary={limite}"


def garantir_casa(api: str, empresa: dict) -> int:
    """Devolve o id da unidade de demo, criando-a se ainda não existir.

    Idempotente de propósito: rodar duas vezes contra produção não duplica
    unidade, e reenviar um período substitui o upload anterior.
    """
    nome = empresa["nome"]
    busca = _requisicao(f"{api}/api/v1/casas?limit=200", None, None, "GET")
    if busca["status"] == 200:
        for casa in json.loads(busca["corpo"])["items"]:
            if casa["nome"] == nome:
                print(f"  unidade já existe: id {casa['id']}")
                return casa["id"]

    corpo = json.dumps(
        {"nome": nome, "marca": empresa["marca"], "cidade": empresa["cidade"], "ativa": True}
    ).encode()
    criada = _requisicao(f"{api}/api/v1/casas", corpo, "application/json", "POST")
    if criada["status"] != 201:
        raise SystemExit(f"Falhei ao criar a unidade ({criada['status']}): {criada['corpo']}")
    casa_id = json.loads(criada["corpo"])["id"]
    print(f"  unidade criada: id {casa_id}")
    return casa_id


def enviar(api: str, casa_id: int, periodo: str, tipo: str, conteudo: bytes) -> None:
    campos = {"casa_id": str(casa_id), "periodo": periodo, "tipo": tipo}
    corpo, content_type = _multipart(campos, f"{tipo}-{periodo}.xlsx", conteudo)
    resposta = _requisicao(f"{api}/api/v1/uploads-custo", corpo, content_type, "POST")
    if resposta["status"] != 201:
        raise SystemExit(f"{periodo} {tipo}: HTTP {resposta['status']} — {resposta['corpo']}")
    return json.loads(resposta["corpo"])["linhas_importadas"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    parser.add_argument(
        "--empresa",
        action="append",
        metavar="SLUG",
        help="Carrega só este slug (pode repetir). Sem a flag, carrega todos",
    )
    parser.add_argument(
        "--apenas-planilhas",
        type=Path,
        metavar="PASTA",
        help="Só grava os .xlsx nesta pasta, sem chamar a API",
    )
    args = parser.parse_args()

    meses, empresas = carregar_catalogo()
    if args.empresa:
        conhecidos = {e["slug"] for e in empresas}
        if desconhecidos := set(args.empresa) - conhecidos:
            raise SystemExit(
                f"slug desconhecido: {', '.join(sorted(desconhecidos))}. "
                f"Disponíveis: {', '.join(sorted(conhecidos))}"
            )
        empresas = [e for e in empresas if e["slug"] in args.empresa]

    if args.apenas_planilhas:
        args.apenas_planilhas.mkdir(parents=True, exist_ok=True)
        ultimo_fator = meses[-1][1]
        for e in empresas:
            (args.apenas_planilhas / f"{e['slug']}-teorico.xlsx").write_bytes(_xlsx(*e["teorico"]))
            (args.apenas_planilhas / f"{e['slug']}-real.xlsx").write_bytes(
                _xlsx(e["real"][0], _escalar_custo(*e["real"], ultimo_fator))
            )
        print(f"{len(empresas) * 2} planilhas gravadas em {args.apenas_planilhas}")
        return

    api = args.api.rstrip("/")
    print(f"API: {api}")
    print(f"{len(empresas)} unidade(s) de demonstração, {len(meses)} meses cada\n")

    resumo = []
    for e in empresas:
        print(f"{e['nome']}  [{e['ramo']}]")
        casa_id = garantir_casa(api, e)
        teorico = _xlsx(*e["teorico"])
        total = 0
        for periodo, fator in meses:
            total += enviar(api, casa_id, periodo, "cardapio", teorico)
            total += enviar(
                api,
                casa_id,
                periodo,
                "compras",
                _xlsx(e["real"][0], _escalar_custo(*e["real"], fator)),
            )
        print(f"  {len(meses) * 2} uploads, {total} linhas\n")
        resumo.append((e["nome"], e["ramo"], casa_id))

    print("Pronto. Unidades carregadas:")
    for nome, ramo, casa_id in resumo:
        print(f"  id {casa_id:<4} {ramo:<26} {nome}")
    print(
        f"\nConfira o fechamento de {meses[-1][0]} de qualquer uma:\n"
        f"  {api}/api/v1/metricas/fechamento?casa_id=<id>&periodo={meses[-1][0]}\n"
        f"  {api}/api/v1/metricas/recomendacao-compra?casa_id=<id>&periodo={meses[-1][0]}"
    )


if __name__ == "__main__":
    main()
