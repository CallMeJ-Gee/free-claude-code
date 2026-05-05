"""Documentation routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_admin_user

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def docs_page(request: Request, admin_user: str = Depends(get_current_admin_user)):
    """Documentation page."""
    return templates.TemplateResponse(
        "docs.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Documentation",
        },
    )
