"""Admin routes aggregate."""

from .dashboard import router as dashboard_router
from .providers import router as providers_router
from .settings import router as settings_router
from .logs import router as logs_router
from .system import router as system_router
from .models import router as models_router
from .routing import router as routing_router
from .welcome import router as welcome_router
from .errors import router as errors_router
from .health import router as health_router
from .diagnostics import router as diagnostics_router
from .cli import router as cli_router
from .metrics import router as metrics_router
from .cli_page import router as cli_page_router
from .health_page import router as health_page_router
from .docs import router as docs_router

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(welcome_router, prefix="/welcome", tags=["welcome"])
router.include_router(dashboard_router, tags=["dashboard"])
router.include_router(providers_router, prefix="/providers", tags=["providers"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
router.include_router(logs_router, prefix="/logs", tags=["logs"])
router.include_router(system_router, prefix="/system", tags=["system"])
router.include_router(models_router, prefix="/models", tags=["models"])
router.include_router(routing_router, prefix="/routing", tags=["routing"])
router.include_router(errors_router, prefix="/errors", tags=["errors"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(diagnostics_router, prefix="/diagnostics", tags=["diagnostics"])
router.include_router(cli_router, prefix="/cli", tags=["cli"])
router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
router.include_router(cli_page_router, prefix="/cli", tags=["cli_page"])
router.include_router(health_page_router, prefix="/health", tags=["health_page"])
router.include_router(docs_router, prefix="/docs", tags=["docs"])
