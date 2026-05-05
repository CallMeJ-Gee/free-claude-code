"""Settings management routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.settings import get_settings
from ..auth import get_current_admin_user
from ..utils import read_env_file, write_env_file, reload_settings

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Settings page."""
    settings = get_settings()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Settings",
            "settings": settings,
        },
    )


@router.post("/")
async def update_settings(data: dict, admin_user: str = Depends(get_current_admin_user)):
    """Update settings."""
    env_vars = read_env_file()

    # Rate limiting
    if "provider_rate_limit" in data:
        env_vars["PROVIDER_RATE_LIMIT"] = str(data["provider_rate_limit"])
    if "provider_rate_window" in data:
        env_vars["PROVIDER_RATE_WINDOW"] = str(data["provider_rate_window"])
    if "provider_max_concurrency" in data:
        env_vars["PROVIDER_MAX_CONCURRENCY"] = str(data["provider_max_concurrency"])

    # Timeouts
    if "http_read_timeout" in data:
        env_vars["HTTP_READ_TIMEOUT"] = str(data["http_read_timeout"])
    if "http_write_timeout" in data:
        env_vars["HTTP_WRITE_TIMEOUT"] = str(data["http_write_timeout"])
    if "http_connect_timeout" in data:
        env_vars["HTTP_CONNECT_TIMEOUT"] = str(data["http_connect_timeout"])

    # Optimizations
    if "enable_network_probe_mock" in data:
        env_vars["ENABLE_NETWORK_PROBE_MOCK"] = "true" if data["enable_network_probe_mock"] else "false"
    if "enable_title_generation_skip" in data:
        env_vars["ENABLE_TITLE_GENERATION_SKIP"] = "true" if data["enable_title_generation_skip"] else "false"
    if "enable_suggestion_mode_skip" in data:
        env_vars["ENABLE_SUGGESTION_MODE_SKIP"] = "true" if data["enable_suggestion_mode_skip"] else "false"
    if "enable_filepath_extraction_mock" in data:
        env_vars["ENABLE_FILEPATH_EXTRACTION_MOCK"] = "true" if data["enable_filepath_extraction_mock"] else "false"

    # Web tools
    if "enable_web_server_tools" in data:
        env_vars["ENABLE_WEB_SERVER_TOOLS"] = "true" if data["enable_web_server_tools"] else "false"
    if "web_fetch_allowed_schemes" in data:
        env_vars["WEB_FETCH_ALLOWED_SCHEMES"] = str(data["web_fetch_allowed_schemes"])
    if "web_fetch_allow_private_networks" in data:
        env_vars["WEB_FETCH_ALLOW_PRIVATE_NETWORKS"] = "true" if data["web_fetch_allow_private_networks"] else "false"

    write_env_file(env_vars)
    reload_settings()

    return {"message": "Settings updated successfully"}


@router.post("/reset")
async def reset_settings(admin_user: str = Depends(get_current_admin_user)):
    """Reset settings to defaults."""
    env_vars = read_env_file()

    # Default values
    defaults = {
        "PROVIDER_RATE_LIMIT": "40",
        "PROVIDER_RATE_WINDOW": "60",
        "PROVIDER_MAX_CONCURRENCY": "5",
        "HTTP_READ_TIMEOUT": "120",
        "HTTP_WRITE_TIMEOUT": "10",
        "HTTP_CONNECT_TIMEOUT": "10",
        "ENABLE_NETWORK_PROBE_MOCK": "true",
        "ENABLE_TITLE_GENERATION_SKIP": "true",
        "ENABLE_SUGGESTION_MODE_SKIP": "true",
        "ENABLE_FILEPATH_EXTRACTION_MOCK": "true",
        "ENABLE_WEB_SERVER_TOOLS": "true",
        "WEB_FETCH_ALLOWED_SCHEMES": "http,https",
        "WEB_FETCH_ALLOW_PRIVATE_NETWORKS": "false",
    }

    for key, value in defaults.items():
        env_vars[key] = value

    write_env_file(env_vars)
    reload_settings()

    return {"message": "Settings reset to defaults"}
