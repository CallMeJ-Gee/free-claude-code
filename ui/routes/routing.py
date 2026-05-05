"""Model routing configuration routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.settings import get_settings
from providers.registry import ProviderRegistry
from ..auth import get_current_admin_user
from ..utils import read_env_file, write_env_file, reload_settings

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Dependency to get the provider registry from app state."""
    return request.app.state.provider_registry


@router.get("/", response_class=HTMLResponse)
async def routing_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Routing page."""
    settings = get_settings()
    registry = get_provider_registry(request)
    models = []
    for provider_id, model_ids in registry.cached_model_ids().items():
        for model_id in sorted(model_ids):
            models.append({
                "provider": provider_id,
                "model": model_id,
                "full_id": f"{provider_id}/{model_id}",
            })

    return templates.TemplateResponse(
        "routing.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Routing",
            "settings": settings,
            "models": models,
        },
    )


@router.post("/")
async def update_routing(
    data: dict,
    admin_user: str = Depends(get_current_admin_user),
):
    """Update routing configuration."""
    env_vars = read_env_file()

    # Default model
    if "model" in data:
        env_vars["MODEL"] = str(data["model"])

    # Tier overrides
    if "model_opus" in data:
        env_vars["MODEL_OPUS"] = str(data["model_opus"])
    if "model_sonnet" in data:
        env_vars["MODEL_SONNET"] = str(data["model_sonnet"])
    if "model_haiku" in data:
        env_vars["MODEL_HAIKU"] = str(data["model_haiku"])

    # Thinking settings
    if "enable_model_thinking" in data:
        env_vars["ENABLE_MODEL_THINKING"] = "true" if data["enable_model_thinking"] else "false"
    if "enable_opus_thinking" in data:
        env_vars["ENABLE_OPUS_THINKING"] = "true" if data["enable_opus_thinking"] else "false"
    if "enable_sonnet_thinking" in data:
        env_vars["ENABLE_SONNET_THINKING"] = "true" if data["enable_sonnet_thinking"] else "false"
    if "enable_haiku_thinking" in data:
        env_vars["ENABLE_HAIKU_THINKING"] = "true" if data["enable_haiku_thinking"] else "false"

    write_env_file(env_vars)
    reload_settings()

    return {"message": "Routing configuration updated successfully"}
