"""Prepara a casa de demonstração, pela API: cardápio REAL, estoque simulado.

    # produção
    uv run python scripts/popular_demo_fechamento.py \
        --api https://app-projeto4-saints2026.azurewebsites.net

    # local (a casa de origem precisa existir no banco local)
    uv run python scripts/popular_demo_fechamento.py

O que faz
---------
1. Acha a casa real de origem (Boteco Sao Bento - Vila Madalena) e os meses em
   que ela tem engenharia de cardápio; usa os últimos 13.
2. Apaga a casa de demonstração, se existir (e a antiga "Boteco Exemplo -
   Pinheiros (DEMO)"), e cria de novo. Cada execução volta ao estado de antes
   da apresentação.
3. Copia, mês a mês, o cardápio por item da casa real para a de demonstração,
   lendo de `GET /metricas/engenharia-cardapio` (só os grupos de CMV e os itens
   com venda de pelo menos R$ 500 no mês) e enviando em `POST /uploads-custo`.
   Os números passam de uma casa para outra pela API: nada do cliente vai para
   disco nem para o Git.
4. Baixa a planilha de fechamento dos meses anteriores ao último — venda e
   teórico somados do cardápio copiado, estoque e compras SIMULADOS
   (`app/services/demo_fechamento.py`) — e envia em `POST /fechamentos`.

O último mês fica para o envio ao vivo, com a planilha que a tela oferece.

Só lê a casa de origem. Só apaga e escreve na casa de demonstração.
"""

import argparse
import io
import json
import os
import sys

# SSLKEYLOGFILE (log de chaves TLS, para depuração) é definida por algumas
# ferramentas no Windows. Com ela, o OpenSSL do Python aborta o processo na
# primeira requisição ("OPENSSL_Uplink ... no OPENSSL_Applink"), mesmo em
# http. Tirar só deste processo não muda nada na máquina.
os.environ.pop("SSLKEYLOGFILE", None)

import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook  # noqa: E402

from app.services import demo_fechamento  # noqa: E402

# O console do Windows abre em cp1252: sem isto, "ç" e "–" derrubam o print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ErroApi(RuntimeError):  # noqa: N818 - nome em português, como o resto do domínio
    pass


def _requisicao(
    url: str, dados: bytes | None = None, tipo: str | None = None, metodo: str = "GET"
) -> bytes:
    req = urllib.request.Request(url, data=dados, method=metodo)
    if tipo:
        req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, timeout=120) as resposta:
            return resposta.read()
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode("utf-8", "replace")
        raise ErroApi(f"{metodo} {url} → {exc.code}: {corpo}") from exc
    except urllib.error.URLError as exc:
        raise ErroApi(f"Não consegui falar com {url}: {exc.reason}. A API está no ar?") from exc


def _json(url: str, dados: dict | None = None, metodo: str = "GET") -> dict:
    corpo = json.dumps(dados).encode() if dados is not None else None
    tipo = "application/json" if dados is not None else None
    return json.loads(_requisicao(url, corpo, tipo, metodo))


def _multipart(campos: dict[str, str], nome_arquivo: str, conteudo: bytes) -> tuple[bytes, str]:
    """Corpo multipart montado à mão para não precisar de `requests` só por isto."""
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


CASA_ANTIGA = "Boteco Exemplo - Pinheiros (DEMO)"
"""A casa de demonstração fictícia, usada até 18/11/2026: apagada se existir."""


def _casas(api: str, busca: str) -> list[dict]:
    consulta = urllib.parse.urlencode({"busca": busca, "limit": 100})
    return _json(f"{api}/api/v1/casas?{consulta}")["items"]


def _cardapio_xlsx(itens: list[dict]) -> bytes:
    livro = Workbook()
    aba = livro.active
    aba.append(["grupo", "subgrupo", "item", "quantidade", "venda_liquida", "custo"])
    for i in itens:
        aba.append(
            [i["grupo"], i["subgrupo"], i["nome"], i["quantidade"], i["venda_liquida"], i["custo"]]
        )
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


def _itens_do_mes(api: str, casa_id: int, periodo: str) -> list[dict]:
    itens: list[dict] = []
    while True:
        consulta = urllib.parse.urlencode(
            {"casa_id": casa_id, "periodo": periodo, "limit": 200, "offset": len(itens)}
        )
        pagina = _json(f"{api}/api/v1/metricas/engenharia-cardapio?{consulta}")
        itens += pagina["items"]
        if not pagina["items"] or len(itens) >= pagina["total"]:
            return itens


def preparar(api: str, origem: str, meses: int) -> None:
    api = api.rstrip("/")
    nome = demo_fechamento.CASA_DEMO["nome"]
    if "(DEMO)" not in nome:  # trava: este script nunca apaga casa real
        raise ErroApi(f"A casa de demonstração precisa ter '(DEMO)' no nome: {nome!r}")

    origens = [c for c in _casas(api, origem) if c["nome"] == origem]
    if not origens:
        raise ErroApi(f"Casa de origem {origem!r} não encontrada em {api}")
    origem_id = origens[0]["id"]
    uploads = _json(f"{api}/api/v1/uploads-custo?casa_id={origem_id}&limit=200")["items"]
    periodos = sorted({u["periodo"] for u in uploads if u["tipo"] == "cardapio"})[-meses:]
    if len(periodos) < 2:
        raise ErroApi(f"{origem!r} tem cardápio em menos de 2 meses")
    print(f"Origem: {origem} (id {origem_id}), {periodos[0]} a {periodos[-1]}.")

    for casa in _casas(api, "(DEMO)"):
        if casa["nome"] in (nome, CASA_ANTIGA):
            _requisicao(f"{api}/api/v1/casas/{casa['id']}", metodo="DELETE")
            print(f"Apagada: {casa['nome']} (id {casa['id']}).")

    casa = _json(f"{api}/api/v1/casas", {**demo_fechamento.CASA_DEMO, "ativa": True}, "POST")
    print(f"Criada: {nome} (id {casa['id']}).")

    for periodo in periodos:
        itens = _itens_do_mes(api, origem_id, periodo)
        corpo, tipo = _multipart(
            {"casa_id": str(casa["id"]), "periodo": periodo, "tipo": "cardapio"},
            f"cardapio-{periodo}.xlsx",
            _cardapio_xlsx(itens),
        )
        _requisicao(f"{api}/api/v1/uploads-custo", corpo, tipo, "POST")
        print(f"  cardápio {periodo}: {len(itens)} itens")

    info = _json(f"{api}/api/v1/modelos/fechamento/demo")
    consulta = urllib.parse.urlencode([("periodo", p) for p in info["periodos_historico"]])
    planilha = _requisicao(f"{api}/api/v1/modelos/fechamento/demo/planilha?{consulta}")
    corpo, tipo = _multipart({"casa_id": str(casa["id"])}, "historico-demo.xlsx", planilha)
    envio = json.loads(_requisicao(f"{api}/api/v1/fechamentos", corpo, tipo, "POST"))
    print(f"Planilha de fechamento enviada: {envio['periodos'][0]} a {envio['periodos'][-1]}.")
    print()
    print(f"Pronto. {info['periodo_ao_vivo']} fica para o envio ao vivo:")
    print("  Fechar o mês → Planilha de fechamento → 'Baixar planilha da demonstração'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    parser.add_argument("--origem", default=demo_fechamento.CASA_ORIGEM, help="Casa real de origem")
    parser.add_argument("--meses", type=int, default=demo_fechamento.MESES)
    args = parser.parse_args()
    try:
        preparar(args.api, args.origem, args.meses)
    except ErroApi as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
