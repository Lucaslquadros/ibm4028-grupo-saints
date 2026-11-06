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
import io
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

NOME = "Drogaria Central - Centro (DEMO)"
MARCA = "Drogaria Central (dado fictício)"
CIDADE = "São Paulo"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# (periodo, fator). O fator move o custo real sem mover a venda, para o ajuste
# variar mês a mês e o gráfico de evolução ter forma — não uma linha reta.
MESES = [
    ("2026-04", 1.00),
    ("2026-05", 1.03),
    ("2026-06", 0.98),
    ("2026-07", 1.06),
    ("2026-08", 1.02),
    ("2026-09", 1.09),
]

# grupo, subgrupo, item, quantidade, venda, custo teórico
CATALOGO = [
    ("MEDICAMENTOS", "GENERICOS", "DIPIRONA 500MG 20CP", 820, 14760, 5904),
    ("MEDICAMENTOS", "GENERICOS", "AMOXICILINA 500MG", 310, 11780, 5301),
    ("MEDICAMENTOS", "REFERENCIA", "LOSARTANA 50MG", 450, 18900, 7560),
    ("PERFUMARIA", "HIGIENE", "SABONETE 90G", 1900, 9500, 4750),
    ("PERFUMARIA", "HIGIENE", "SHAMPOO 350ML", 540, 13500, 7290),
    ("PERFUMARIA", "INFANTIL", "FRALDA M 30UN", 260, 15600, 9360),
]
# Só no lado real: custo indireto, sem venda. O equivalente a UTENSILIOS na DRE
# do restaurante — a dedução de grupos tem que deixar isto fora do CMV.
INDIRETOS = [("EMBALAGENS", "DESCARTAVEIS", 2100)]


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


def planilha_teorico() -> bytes:
    """Lado teórico: vendas × custo de ficha. Tem venda, então tem denominador."""
    return _xlsx(
        ["Grupo", "Subgrupo", "Item", "Quantidade", "Venda Líquida", "Custo"],
        [[g, s, i, q, v, c] for g, s, i, q, v, c in CATALOGO],
    )


def planilha_real(fator: float) -> bytes:
    """Lado real: o que de fato foi comprado. Sem coluna de venda — um relatório
    de compras não tem receita, e o leitor aceita porque só grupo e custo são
    obrigatórios."""
    linhas = [[g, s, round(c * fator, 2)] for g, s, _, _, _, c in CATALOGO]
    linhas += [[g, s, c] for g, s, c in INDIRETOS]
    return _xlsx(["Grupo", "Subgrupo", "Custo"], linhas)


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


def garantir_casa(api: str) -> int:
    """Devolve o id da unidade de demo, criando-a se ainda não existir."""
    import json

    busca = _requisicao(f"{api}/api/v1/casas?busca=Drogaria&limit=50", None, None, "GET")
    if busca["status"] == 200:
        for casa in json.loads(busca["corpo"])["items"]:
            if casa["nome"] == NOME:
                print(f"Unidade de demo já existe: id {casa['id']}")
                return casa["id"]

    corpo = json.dumps({"nome": NOME, "marca": MARCA, "cidade": CIDADE, "ativa": True}).encode()
    criada = _requisicao(f"{api}/api/v1/casas", corpo, "application/json", "POST")
    if criada["status"] != 201:
        raise SystemExit(f"Falhei ao criar a unidade ({criada['status']}): {criada['corpo']}")
    casa_id = json.loads(criada["corpo"])["id"]
    print(f"Unidade de demo criada: id {casa_id} — {NOME}")
    return casa_id


def enviar(api: str, casa_id: int, periodo: str, tipo: str, conteudo: bytes) -> None:
    import json

    campos = {"casa_id": str(casa_id), "periodo": periodo, "tipo": tipo}
    corpo, content_type = _multipart(campos, f"{tipo}-{periodo}.xlsx", conteudo)
    resposta = _requisicao(f"{api}/api/v1/uploads-custo", corpo, content_type, "POST")
    if resposta["status"] != 201:
        raise SystemExit(f"{periodo} {tipo}: HTTP {resposta['status']} — {resposta['corpo']}")
    print(f"  {periodo} {tipo:8s} → {json.loads(resposta['corpo'])['linhas_importadas']} linhas")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    parser.add_argument(
        "--apenas-planilhas",
        type=Path,
        help="Só grava os .xlsx nesta pasta, sem chamar a API",
    )
    args = parser.parse_args()

    if args.apenas_planilhas:
        args.apenas_planilhas.mkdir(parents=True, exist_ok=True)
        (args.apenas_planilhas / "template-teorico.xlsx").write_bytes(planilha_teorico())
        (args.apenas_planilhas / "template-real.xlsx").write_bytes(planilha_real(1.09))
        print(f"Planilhas gravadas em {args.apenas_planilhas}")
        return

    api = args.api.rstrip("/")
    print(f"API: {api}")
    casa_id = garantir_casa(api)
    for periodo, fator in MESES:
        enviar(api, casa_id, periodo, "cardapio", planilha_teorico())
        enviar(api, casa_id, periodo, "compras", planilha_real(fator))

    print(
        f"\nPronto. Confira o fechamento:\n"
        f"  {api}/api/v1/metricas/fechamento?casa_id={casa_id}&periodo=2026-09\n"
        f"  {api}/api/v1/metricas/evolucao?casa_id={casa_id}"
    )


if __name__ == "__main__":
    main()
