"""Health check.

O Azure App Service chama esta rota periodicamente. Se ela parar de responder,
o Azure reinicia a instância sozinho. Sem este endpoint, uma aplicação travada
continua recebendo tráfego e devolvendo erro.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import AppSettings, DbSession
from app.schemas import HealthResponse

router = APIRouter(tags=["infra"])


@router.get("/health", summary="Health check")
def health_check(db: DbSession, settings: AppSettings) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        banco = "ok"
    except Exception as exc:  # noqa: BLE001 - health check nunca pode estourar
        banco = f"erro: {type(exc).__name__}"

    return HealthResponse(
        status="ok" if banco == "ok" else "degraded",
        versao=settings.app_version,
        ambiente=settings.environment,
        banco=banco,
        # O workflow de deploy compara este valor com o SHA que acabou de
        # publicar. Sem ele, "deploy verificado" só provava que a aplicação
        # estava de pé — podia estar de pé com o código anterior.
        commit=settings.git_commit,
    )
