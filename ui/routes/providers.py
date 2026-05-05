"""Provider management routes."""

import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config.settings import get_settings
from providers.registry import ProviderRegistry
from ..auth import get_current_admin_user
from ..utils import read_env_file, write_env_file, reload_settings

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Cache TTL in seconds
PROVIDERS_CACHE_TTL = 60
_providers_cache = {"data": None, "timestamp": 0}


def clear_providers_cache() -> None:
    """Clear the providers cache."""
    _providers_cache["data"] = None
    _providers_cache["timestamp"] = 0


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Dependency to get the provider registry from app state."""
    return request.app.state.provider_registry


# Provider type to environment variable mappings
PROVIDER_ENV_MAPPINGS = {
    "nvidia_nim": {
        "api_key": "NVIDIA_NIM_API_KEY",
        "base_url": None,  # NVIDIA NIM uses default URL
        "proxy": "NVIDIA_NIM_PROXY",
    },
    "open_router": {
        "api_key": "OPENROUTER_API_KEY",
        "base_url": None,
        "proxy": "OPENROUTER_PROXY",
    },
    "deepseek": {
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": None,
        "proxy": None,
    },
    "lmstudio": {
        "api_key": None,
        "base_url": "LM_STUDIO_BASE_URL",
        "proxy": "LMSTUDIO_PROXY",
    },
    "llamacpp": {
        "api_key": None,
        "base_url": "LLAMACPP_BASE_URL",
        "proxy": "LLAMACPP_PROXY",
    },
    "ollama": {
        "api_key": None,
        "base_url": "OLLAMA_BASE_URL",
        "proxy": None,
    },
}


@router.get("/", response_class=HTMLResponse)
async def providers_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Providers management page."""
    return templates.TemplateResponse(
        "providers.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Providers",
        },
    )


@router.get("/list")
async def list_providers(
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """List all configured providers."""
    current_time = time.time()

    # Check cache
    if _providers_cache["data"] and (current_time - _providers_cache["timestamp"] < PROVIDERS_CACHE_TTL):
        return _providers_cache["data"]

    providers = []
    for provider_id in registry.cached_model_ids():
        providers.append({
            "id": provider_id,
            "models_count": len(registry.cached_model_ids().get(provider_id, [])),
        })

    result = {"providers": providers}

    # Update cache
    _providers_cache["data"] = result
    _providers_cache["timestamp"] = current_time

    return result


@router.get("/form", response_class=HTMLResponse)
async def provider_form(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Add/Edit provider form."""
    return templates.TemplateResponse(
        "provider_form.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Add Provider",
        },
    )


@router.post("/")
async def create_provider(
    data: dict,
    admin_user: str = Depends(get_current_admin_user),
):
    """Create a new provider."""
    provider_type = data.get("provider_type")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")
    proxy = data.get("proxy", "")

    if not provider_type:
        raise HTTPException(status_code=400, detail="provider_type is required")

    if provider_type not in PROVIDER_ENV_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider type: {provider_type}")

    mapping = PROVIDER_ENV_MAPPINGS[provider_type]
    env_vars = read_env_file()

    # Update API key if applicable
    if mapping["api_key"] and api_key:
        env_vars[mapping["api_key"]] = api_key

    # Update base URL if applicable
    if mapping["base_url"] and base_url:
        env_vars[mapping["base_url"]] = base_url

    # Update proxy if applicable
    if mapping["proxy"] and proxy:
        env_vars[mapping["proxy"]] = proxy

    write_env_file(env_vars)
    reload_settings()

    # Clear caches
    clear_providers_cache()

    return {"message": "Provider created successfully"}


@router.put("/{provider_id}")
async def update_provider(
    provider_id: str,
    data: dict,
    admin_user: str = Depends(get_current_admin_user),
):
    """Update a provider."""
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")
    proxy = data.get("proxy", "")

    if provider_id not in PROVIDER_ENV_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    mapping = PROVIDER_ENV_MAPPINGS[provider_id]
    env_vars = read_env_file()

    # Update API key if provided
    if mapping["api_key"] and api_key:
        env_vars[mapping["api_key"]] = api_key

    # Update base URL if provided
    if mapping["base_url"] and base_url:
        env_vars[mapping["base_url"]] = base_url

    # Update proxy if provided
    if mapping["proxy"] and proxy:
        env_vars[mapping["proxy"]] = proxy

    write_env_file(env_vars)
    reload_settings()

    # Clear caches
    clear_providers_cache()

    return {"message": "Provider updated successfully"}


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    admin_user: str = Depends(get_current_admin_user),
):
    """Delete a provider."""
    if provider_id not in PROVIDER_ENV_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    mapping = PROVIDER_ENV_MAPPINGS[provider_id]
    env_vars = read_env_file()

    # Clear API key
    if mapping["api_key"] and mapping["api_key"] in env_vars:
        env_vars[mapping["api_key"]] = ""

    # Clear base URL
    if mapping["base_url"] and mapping["base_url"] in env_vars:
        env_vars[mapping["base_url"]] = ""

    # Clear proxy
    if mapping["proxy"] and mapping["proxy"] in env_vars:
        env_vars[mapping["proxy"]] = ""

    write_env_file(env_vars)
    reload_settings()

    # Clear caches
    clear_providers_cache()

    return {"message": "Provider deleted successfully"}


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: str,
    admin_user: str = Depends(get_current_admin_user),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    """Test provider connection."""
    try:
        provider = registry.get(provider_id, get_settings())
        # Try to fetch models as a test
        await provider.list_model_infos()
        return {"status": "ok", "message": "Connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
