"""Logs viewing routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_admin_user

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Log file path
_log_file_path = Path("server.log")


@router.get("/", response_class=HTMLResponse)
async def logs_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Logs page."""
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Logs",
        },
    )


@router.get("/stream")
async def stream_logs(
    level: str = "INFO",
    filter: str = "",
    admin_user: str = Depends(get_current_admin_user),
):
    """Get recent logs (for polling)."""
    log_file = _log_file_path
    if not log_file.exists():
        return "No log file found"

    lines = []
    try:
        with open(log_file, 'r') as f:
            # Read all lines
            all_lines = f.readlines()

            # Filter by level
            if level != "DEBUG":
                lines = [line for line in all_lines if f"[{level}]" in line or level not in ["INFO", "WARNING", "ERROR"]]
            else:
                lines = all_lines

            # Filter by request_id
            if filter:
                lines = [line for line in lines if filter in line]

            # Return last 100 lines
            lines = lines[-100:]

    except Exception as e:
        return f"Failed to read log file: {str(e)}"

    return "\n".join(lines)


@router.get("/recent", response_class=HTMLResponse)
async def recent_errors(
    level: str = "ERROR",
    limit: int = 10,
    admin_user: str = Depends(get_current_admin_user),
):
    """Get recent errors as HTML fragment for dashboard."""
    from pathlib import Path

    log_file = Path("server.log")
    if not log_file.exists():
        return '<div class="text-gray-500">No log file found</div>'

    # Read last 100 lines
    lines = []
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()[-100:]  # Last 100 lines
    except Exception:
        return '<div class="text-gray-500">Failed to read log file</div>'

    # Filter by level
    if level != "DEBUG":
        lines = [line for line in lines if f"[{level}]" in line or level not in ["INFO", "WARNING", "ERROR"]]

    # Take last N lines
    lines = lines[-limit:]

    if not lines:
        return '<div class="text-gray-500">No recent errors</div>'

    # Format as HTML
    html_lines = []
    for line in lines:
        html_lines.append(f'<div class="text-sm font-mono bg-gray-50 p-2 rounded mb-1">{line.strip()}</div>')

    return "\n".join(html_lines)
