"""CLI command execution routes."""

import asyncio
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import get_current_admin_user

router = APIRouter()

# Command history
_command_history = []
_max_history = 50


@router.post("/execute")
async def execute_command(
    command: str,
    admin_user: str = Depends(get_current_admin_user),
):
    """Execute a CLI command."""
    # Add to history
    _command_history.append({
        "command": command,
        "timestamp": datetime.now().isoformat(),
    })
    if len(_command_history) > _max_history:
        _command_history.pop(0)

    # Validate command
    allowed_commands = [
        "status",
        "start",
        "stop",
        "restart",
        "logs",
        "config",
        "version",
    ]

    command_parts = command.split()
    if not command_parts:
        return {"output": "", "error": "No command provided"}

    base_command = command_parts[0]
    if base_command not in allowed_commands:
        return {"output": "", "error": f"Command '{base_command}' not allowed"}

    try:
        # Execute command
        process = await asyncio.create_subprocess_exec(
            *command_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path.cwd(),
        )

        stdout, stderr = await process.communicate()

        output = stdout.decode() if stdout else ""
        error = stderr.decode() if stderr else ""

        return {
            "output": output,
            "error": error,
            "exit_code": process.returncode,
        }
    except Exception as e:
        return {"output": "", "error": str(e)}


@router.get("/history")
async def get_command_history(admin_user: str = Depends(get_current_admin_user)):
    """Get command history."""
    return {"history": _command_history}


@router.post("/restart")
async def restart_server(admin_user: str = Depends(get_current_admin_user)):
    """Restart the server."""
    try:
        # Send SIGTERM to self for graceful shutdown
        # The process manager (systemd, docker, etc.) should restart it
        os.kill(os.getpid(), signal.SIGTERM)
        return {"message": "Restart signal sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config(admin_user: str = Depends(get_current_admin_user)):
    """Reload configuration."""
    try:
        from ..utils import reload_settings
        reload_settings()
        return {"message": "Configuration reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(admin_user: str = Depends(get_current_admin_user)):
    """Get server status."""
    try:
        import psutil
        process = psutil.Process()

        return {
            "status": "running",
            "pid": process.pid,
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
            "thread_count": process.num_threads(),
            "uptime": _get_uptime(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_uptime() -> str:
    """Get formatted uptime string."""
    try:
        import psutil
        process = psutil.Process()
        uptime_seconds = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        secs = int(uptime_seconds % 60)
        return f"{hours}h {minutes}m {secs}s"
    except Exception:
        return "unknown"
