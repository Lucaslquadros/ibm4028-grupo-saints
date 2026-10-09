"""Testa a rede de segurança de app/main.py: erro não tratado vira 500
genérico, sem vazar stack trace na resposta HTTP — e o stack trace real
ainda vai para o log (regra 9 do CLAUDE.md).
"""

import logging

from app import crud

BASE = "/api/v1/casas"


def test_erro_nao_tratado_devolve_500_generico(client_sem_raise, monkeypatch):
    def _explode(*args, **kwargs):
        raise RuntimeError("segredo interno: senha=abc123")

    monkeypatch.setattr(crud, "listar_casas", _explode)

    resposta = client_sem_raise.get(BASE)

    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno do servidor"}
    # nada do erro original pode escapar para o cliente
    assert "segredo" not in resposta.text
    assert "RuntimeError" not in resposta.text
    assert "Traceback" not in resposta.text


def test_erro_nao_tratado_registra_stack_trace_no_log(client_sem_raise, monkeypatch, caplog):
    def _explode(*args, **kwargs):
        raise RuntimeError("segredo interno: senha=abc123")

    monkeypatch.setattr(crud, "listar_casas", _explode)

    with caplog.at_level(logging.ERROR, logger="projeto4"):
        client_sem_raise.get(BASE)

    assert "Erro não tratado" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "Traceback" in caplog.text
