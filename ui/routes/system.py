"""System management routes."""

import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from providers.registry import ProviderRegistry
from config.settings import get_settings

from ..auth import get_current_admin_user

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Cache TTL in seconds
SYSTEM_STATUS_CACHE_TTL = 30
_provider_status_cache = {"data": None, "timestamp": 0}


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Dependency to get the provider registry from app state."""
    return request.app.state.provider_registry


@router.get("/", response_class=HTMLResponse)
async def system_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """System management page."""
    return templates.TemplateResponse(
        "system.html",
        {
            "request": request,
            "username": admin_user,
            "title": "System",
        },
    )


@router.get("/status")
async def system_status(
    request: Request,
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """Get system status for dashboard."""
    current_time = time.time()

    # Check cache
    if _provider_status_cache["data"] and (current_time - _provider_status_cache["timestamp"] < SYSTEM_STATUS_CACHE_TTL):
        return _provider_status_cache["data"]

    settings = get_settings()

    # Build provider health info
    cached_providers = registry.cached_model_ids()
    providers_info = []
    for provider_id, model_ids in cached_providers.items():
        providers_info.append({
            "id": provider_id,
            "healthy": True,  # TODO: actual health check via test request
            "last_check": datetime.now().strftime("%H:%M:%S"),
            "error_count": 0,
            "model_count": len(model_ids),
        })

    # Get uptime from app state if available
    app_start_time = getattr(request.app.state, 'start_time', None)
    uptime_str = "N/A"
    if app_start_time:
        uptime_seconds = time.time() - app_start_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        secs = int(uptime_seconds % 60)
        uptime_str = f"{hours}h {minutes}m {secs}s"

    result = {
        "status": "ok",
        "uptime": uptime_str,
        "providers": providers_info,
        "timestamp": datetime.now().isoformat(),
        "total_providers": len(cached_providers),
        "total_models": sum(len(models) for models in cached_providers.values()),
    }

    # Update cache
    _provider_status_cache["data"] = result
    _provider_status_cache["timestamp"] = current_time

    return result


@router.post("/clear-cache")
async def clear_cache(
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """Clear provider model cache."""
    registry._model_ids_by_provider.clear()
    registry._model_infos_by_provider.clear()
    # Clear system status cache
    _provider_status_cache["data"] = None
    _provider_status_cache["timestamp"] = 0
    return {"message": "Model cache cleared"}


@router.post("/restart")
async def restart(
    admin_user: str = Depends(get_current_admin_user),
):
    """Request graceful restart."""
    import os
    import signal
    import sys

    # Send SIGTERM to self for graceful shutdown
    # The process manager (systemd, docker, etc.) should restart it
    os.kill(os.getpid(), signal.SIGTERM)

    return {"message": "Restart signal sent"}


@router.get("/config")
async def view_config(
    admin_user: str = Depends(get_current_admin_user),
    settings: get_settings = Depends(get_settings),
):
    """View effective configuration (secrets masked)."""
    # Exclude sensitive fields
    sensitive = {"anthropic_auth_token", "nvidia_nim_api_key", "open_router_api_key",
                 "deepseek_api_key", "telegram_bot_token", "discord_bot_token",
                 "admin_password_hash", "hf_token"}
    config = settings.model_dump()
    for key in sensitive:
        if key in config and config[key]:
            config[key] = "***"
    return config
