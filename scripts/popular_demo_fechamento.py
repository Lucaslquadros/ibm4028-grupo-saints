"""Prepara a casa de demonstração da planilha de fechamento, pela API.

    # local (API subida com `uv run fastapi dev app/main.py`)
    uv run python scripts/popular_demo_fechamento.py

    # produção
    uv run python scripts/popular_demo_fechamento.py \
        --api https://app-projeto4-saints2026.azurewebsites.net

O que faz
---------
1. Apaga a casa "Boteco Exemplo - Pinheiros (DEMO)", se existir, e cria de
   novo. Assim dá para ensaiar o envio ao vivo quantas vezes quiser: cada
   execução volta ao estado de antes da apresentação.
2. Baixa da própria API a planilha do histórico (abr–ago/26) e envia em
   `POST /api/v1/fechamentos`, exatamente como a tela faria.

O mês da apresentação (set/26) fica de fora: ele é enviado ao vivo pela tela
de Upload, com a planilha que a própria tela oferece para baixar. Os dados são
fictícios — estão em `app/services/demo_fechamento.py`.

Só toca a casa de demonstração. Nenhuma outra casa é lida, alterada ou apagada.
"""

import argparse
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


def preparar(api: str) -> None:
    api = api.rstrip("/")
    info = _json(f"{api}/api/v1/modelos/fechamento/demo")
    nome = info["casa_nome"]
    if "(DEMO)" not in nome:  # trava: este script nunca toca casa real
        raise ErroApi(f"A casa de demonstração precisa ter '(DEMO)' no nome: {nome!r}")

    busca = urllib.parse.urlencode({"busca": "(DEMO)", "limit": 100})
    for casa in _json(f"{api}/api/v1/casas?{busca}")["items"]:
        if casa["nome"] == nome:
            _requisicao(f"{api}/api/v1/casas/{casa['id']}", metodo="DELETE")
            print(f"Casa anterior apagada (id {casa['id']}).")

    casa = _json(
        f"{api}/api/v1/casas",
        {"nome": nome, "marca": "Boteco Exemplo", "cidade": "Sao Paulo", "ativa": True},
        "POST",
    )
    print(f"Casa criada: {nome} (id {casa['id']}).")

    meses = urllib.parse.urlencode([("periodo", p) for p in info["periodos_historico"]])
    planilha = _requisicao(f"{api}/api/v1/modelos/fechamento/demo/planilha?{meses}")
    corpo, tipo = _multipart({"casa_id": str(casa["id"])}, "historico-demo.xlsx", planilha)
    envio = json.loads(_requisicao(f"{api}/api/v1/fechamentos", corpo, tipo, "POST"))
    print(
        f"Histórico enviado: {', '.join(envio['periodos'])} ({envio['linhas_importadas']} linhas)."
    )
    print(
        f"\nPronto. Na apresentação: aba Upload → casa '{nome}' → "
        f"'Planilha de fechamento' → baixar a planilha de {info['periodo_ao_vivo']} → enviar."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    args = parser.parse_args()
    try:
        preparar(args.api)
    except ErroApi as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
