"""Model discovery routes."""

import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from providers.registry import ProviderRegistry
from ..auth import get_current_admin_user

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Cache TTL in seconds
MODELS_CACHE_TTL = 60
_models_cache = {"data": None, "timestamp": 0}


def clear_models_cache() -> None:
    """Clear the models cache."""
    _models_cache["data"] = None
    _models_cache["timestamp"] = 0


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Dependency to get the provider registry from app state."""
    return request.app.state.provider_registry


@router.get("/", response_class=HTMLResponse)
async def models_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Models page."""
    return templates.TemplateResponse(
        "models.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Models",
        },
    )


@router.get("/details", response_class=HTMLResponse)
async def model_details_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Model details page."""
    return templates.TemplateResponse(
        "model_details.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Model Details",
        },
    )


@router.get("/list")
async def list_models(
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """List all discovered models."""
    current_time = time.time()

    # Check cache
    if _models_cache["data"] and (current_time - _models_cache["timestamp"] < MODELS_CACHE_TTL):
        return _models_cache["data"]

    cached = registry.cached_model_ids()
    models = []
    for provider_id, model_ids in cached.items():
        for model_id in sorted(model_ids):
            models.append({
                "provider": provider_id,
                "model": model_id,
                "full_id": f"{provider_id}/{model_id}",
            })

    result = {"models": models, "total": len(models)}

    # Update cache
    _models_cache["data"] = result
    _models_cache["timestamp"] = current_time

    return result
