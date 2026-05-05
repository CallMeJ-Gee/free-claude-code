"""Admin dashboard route."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import AdminUser

router = APIRouter()

templates = Jinja2Templates(directory="ui/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, admin_user: AdminUser):
    """Admin dashboard home page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": admin_user,
            "title": "Dashboard",
        },
    )
