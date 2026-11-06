"""Ponto de entrada da aplicação.

Rodar local:  uv run fastapi dev app/main.py
Docs:         http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import criar_tabelas
from app.routers import casas, health, metricas, uploads

# Logging estruturado: em produção o Application Insights captura isto sozinho.
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("projeto4")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup. Enquanto não há Alembic, criamos as tabelas que faltam.
    criar_tabelas()
    logger.info("API iniciada | ambiente=%s versao=%s", settings.environment, settings.app_version)
    yield
    # Shutdown
    logger.info("API encerrada")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API do Projeto em Ciência de Dados IV — IBM4028 / IBMEC CDIA 2026.2.\n\n"
        "Documentação interativa em `/docs`, contrato OpenAPI em `/openapi.json`."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: o erro não vem do backend, vem do navegador. Configure desde o início.
# Em produção, NUNCA use ["*"] — liste o domínio real do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(casas.router)
app.include_router(uploads.router)
app.include_router(metricas.router)


@app.get("/", tags=["infra"], summary="Raiz")
async def raiz() -> dict:
    """Ponto de entrada: diz onde está a documentação e onde está a aplicação.

    Antes havia aqui um `/painel` servindo `frontend/painel-teste.html`, o painel
    descartável de antes do frontend React. O arquivo foi para `frontend/public/`
    quando o Vite entrou, e a rota passou a devolver 500 — anunciada por esta
    própria resposta. Removida: quem serve a interface é o Static Web App.
    """
    corpo = {
        "aplicacao": settings.app_name,
        "versao": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
    if settings.frontend_url:
        corpo["aplicacao_web"] = settings.frontend_url
    return corpo


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, exc: Exception) -> JSONResponse:
    """Rede de segurança: qualquer exceção não prevista vira um 500 com formato
    conhecido. O stack trace vai para o log, nunca para o cliente — mensagem de
    erro detalhada em resposta HTTP é vazamento de informação."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )
