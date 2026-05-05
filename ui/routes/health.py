"""Health check and monitoring routes."""

import os
import psutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from config.settings import get_settings
from providers.registry import ProviderRegistry
from ..auth import get_current_admin_user

router = APIRouter()


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Dependency to get the provider registry from app state."""
    return request.app.state.provider_registry


@router.get("/")
async def health_check(
    request: Request,
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """Comprehensive health check."""
    settings = get_settings()

    # System health
    system_health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": _get_uptime(request),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "platform": os.uname().sysname,
    }

    # Resource usage
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        system_health["resources"] = {
            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
            "cpu_percent": round(cpu_percent, 2),
            "thread_count": process.num_threads(),
        }
    except Exception:
        system_health["resources"] = {
            "memory_mb": "unknown",
            "cpu_percent": "unknown",
            "thread_count": "unknown",
        }

    # Configuration health
    config_health = {
        "status": "ok",
        "issues": [],
    }

    # Check if at least one provider is configured
    cached_providers = registry.cached_model_ids()
    if not cached_providers:
        config_health["status"] = "warning"
        config_health["issues"].append("No providers configured")

    # Check if default model is set
    if not settings.model:
        config_health["status"] = "warning"
        config_health["issues"].append("No default model configured")

    # Check if auth token is set
    if not settings.anthropic_auth_token:
        config_health["status"] = "warning"
        config_health["issues"].append("No auth token configured (insecure)")

    system_health["configuration"] = config_health

    # Provider health
    provider_health = []
    for provider_id, model_ids in cached_providers.items():
        provider_health.append({
            "id": provider_id,
            "status": "ok",
            "models_count": len(model_ids),
            "last_check": datetime.now().strftime("%H:%M:%S"),
        })

    system_health["providers"] = provider_health

    # Overall status
    if config_health["status"] == "warning":
        system_health["status"] = "warning"
    elif not provider_health:
        system_health["status"] = "degraded"

    return system_health


@router.get("/providers")
async def provider_health(
    registry: ProviderRegistry = Depends(get_provider_registry),
    admin_user: str = Depends(get_current_admin_user),
):
    """Check health of all configured providers."""
    cached_providers = registry.cached_model_ids()
    settings = get_settings()

    providers = []
    for provider_id in cached_providers:
        try:
            provider = registry.get(provider_id, settings)
            # Try to fetch models as a health check
            await provider.list_model_infos()
            providers.append({
                "id": provider_id,
                "status": "healthy",
                "models_count": len(cached_providers[provider_id]),
                "last_check": datetime.now().isoformat(),
            })
        except Exception as e:
            providers.append({
                "id": provider_id,
                "status": "unhealthy",
                "error": str(e),
                "models_count": len(cached_providers[provider_id]),
                "last_check": datetime.now().isoformat(),
            })

    return {"providers": providers}


@router.get("/config")
async def config_health(admin_user: str = Depends(get_current_admin_user)):
    """Check configuration health."""
    settings = get_settings()

    issues = []
    warnings = []

    # Check required configuration
    if not settings.model:
        issues.append("No default model configured")

    # Check provider configuration
    has_provider = False
    if settings.nvidia_nim_api_key:
        has_provider = True
    if settings.open_router_api_key:
        has_provider = True
    if settings.deepseek_api_key:
        has_provider = True
    if settings.lm_studio_base_url:
        has_provider = True
    if settings.llamacpp_base_url:
        has_provider = True
    if settings.ollama_base_url:
        has_provider = True

    if not has_provider:
        issues.append("No provider configured")

    # Check security
    if not settings.anthropic_auth_token:
        warnings.append("No auth token configured (insecure)")

    # Check rate limits
    if settings.provider_rate_limit < 1:
        warnings.append("Provider rate limit is very low")

    # Check timeouts
    if settings.http_read_timeout < 30:
        warnings.append("Read timeout is very low")

    return {
        "status": "ok" if not issues else "error",
        "issues": issues,
        "warnings": warnings,
        "configured_providers": has_provider,
    }


def _get_uptime(request: Request) -> str:
    """Get formatted uptime string."""
    app_start_time = getattr(request.app.state, 'start_time', None)
    if not app_start_time:
        return "unknown"

    import time
    uptime_seconds = time.time() - app_start_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    secs = int(uptime_seconds % 60)

    return f"{hours}h {minutes}m {secs}s"
