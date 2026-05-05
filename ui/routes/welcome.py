"""Welcome/onboarding routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_admin_user
from ..utils import read_env_file, write_env_file, reload_settings

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def welcome_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Welcome/onboarding page."""
    return templates.TemplateResponse(
        "welcome.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Welcome",
        },
    )


@router.post("/settings/preset/{preset_name}")
async def apply_preset(
    preset_name: str,
    admin_user: str = Depends(get_current_admin_user),
):
    """Apply a configuration preset."""
    presets = {
        "free": {
            "provider_rate_limit": 1,
            "provider_rate_window": 3,
            "provider_max_concurrency": 2,
            "http_read_timeout": 120,
            "http_write_timeout": 10,
            "http_connect_timeout": 10,
            "enable_network_probe_mock": True,
            "enable_title_generation_skip": True,
            "enable_suggestion_mode_skip": True,
            "enable_filepath_extraction_mock": True,
            "enable_web_server_tools": True,
            "web_fetch_allowed_schemes": "http,https",
            "web_fetch_allow_private_networks": False,
        },
        "local": {
            "provider_rate_limit": 10,
            "provider_rate_window": 60,
            "provider_max_concurrency": 5,
            "http_read_timeout": 300,
            "http_write_timeout": 10,
            "http_connect_timeout": 10,
            "enable_network_probe_mock": True,
            "enable_title_generation_skip": True,
            "enable_suggestion_mode_skip": True,
            "enable_filepath_extraction_mock": True,
            "enable_web_server_tools": True,
            "web_fetch_allowed_schemes": "http,https",
            "web_fetch_allow_private_networks": True,
        },
        "mixed": {
            "provider_rate_limit": 3,
            "provider_rate_window": 60,
            "provider_max_concurrency": 5,
            "http_read_timeout": 180,
            "http_write_timeout": 10,
            "http_connect_timeout": 10,
            "enable_network_probe_mock": True,
            "enable_title_generation_skip": True,
            "enable_suggestion_mode_skip": True,
            "enable_filepath_extraction_mock": True,
            "enable_web_server_tools": True,
            "web_fetch_allowed_schemes": "http,https",
            "web_fetch_allow_private_networks": False,
        },
    }

    if preset_name not in presets:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Unknown preset: {preset_name}"}
        )

    preset = presets[preset_name]
    env_vars = read_env_file()

    # Map preset keys to env variable names
    env_mappings = {
        "provider_rate_limit": "PROVIDER_RATE_LIMIT",
        "provider_rate_window": "PROVIDER_RATE_WINDOW",
        "provider_max_concurrency": "PROVIDER_MAX_CONCURRENCY",
        "http_read_timeout": "HTTP_READ_TIMEOUT",
        "http_write_timeout": "HTTP_WRITE_TIMEOUT",
        "http_connect_timeout": "HTTP_CONNECT_TIMEOUT",
        "enable_network_probe_mock": "ENABLE_NETWORK_PROBE_MOCK",
        "enable_title_generation_skip": "ENABLE_TITLE_GENERATION_SKIP",
        "enable_suggestion_mode_skip": "ENABLE_SUGGESTION_MODE_SKIP",
        "enable_filepath_extraction_mock": "ENABLE_FILEPATH_EXTRACTION_MOCK",
        "enable_web_server_tools": "ENABLE_WEB_SERVER_TOOLS",
        "web_fetch_allowed_schemes": "WEB_FETCH_ALLOWED_SCHEMES",
        "web_fetch_allow_private_networks": "WEB_FETCH_ALLOW_PRIVATE_NETWORKS",
    }

    for key, value in preset.items():
        env_key = env_mappings.get(key)
        if env_key:
            env_vars[env_key] = str(value)

    write_env_file(env_vars)
    reload_settings()

    return {"message": f"Preset '{preset_name}' applied successfully"}
