"""Error logging and management routes."""

import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from loguru import logger

from ..auth import get_current_admin_user

router = APIRouter()

# Error log storage (in-memory with TTL)
_error_log = []
_max_error_entries = 1000
_error_log_ttl = 3600  # 1 hour


def log_error(
    error_type: str,
    message: str,
    severity: str = "error",
    context: dict | None = None,
) -> None:
    """Log an error to the admin error log."""
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "message": message,
        "severity": severity,
        "context": context or {},
    }
    _error_log.append(error_entry)

    # Trim log if too large
    if len(_error_log) > _max_error_entries:
        _error_log.pop(0)

    # Also log to file
    log_func = logger.error if severity == "error" else logger.warning
    log_func(f"Admin UI Error: {error_type} - {message}")


def cleanup_old_errors() -> None:
    """Remove errors older than TTL."""
    current_time = time.time()
    cutoff_time = current_time - _error_log_ttl

    # Convert ISO timestamps to Unix time for comparison
    def timestamp_to_unix(ts: str) -> float:
        try:
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return 0

    while _error_log and timestamp_to_unix(_error_log[0]["timestamp"]) < cutoff_time:
        _error_log.pop(0)


@router.get("/list")
async def list_errors(
    limit: int = 100,
    severity: str | None = None,
    admin_user: str = Depends(get_current_admin_user),
):
    """List recent errors."""
    cleanup_old_errors()

    errors = _error_log.copy()

    # Filter by severity if specified
    if severity:
        errors = [e for e in errors if e["severity"] == severity]

    # Limit results
    errors = errors[-limit:] if len(errors) > limit else errors

    # Reverse to show newest first
    errors.reverse()

    return {
        "errors": errors,
        "total": len(_error_log),
        "filtered": len(errors),
    }


@router.get("/stats")
async def error_stats(admin_user: str = Depends(get_current_admin_user)):
    """Get error statistics."""
    cleanup_old_errors()

    stats = {
        "total": len(_error_log),
        "by_severity": {},
        "by_type": {},
        "recent": [],
    }

    for error in _error_log:
        # Count by severity
        severity = error["severity"]
        stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

        # Count by type
        error_type = error["error_type"]
        stats["by_type"][error_type] = stats["by_type"].get(error_type, 0) + 1

    # Get recent errors (last 10)
    stats["recent"] = _error_log[-10:] if len(_error_log) > 10 else _error_log
    stats["recent"].reverse()

    return stats


@router.post("/clear")
async def clear_errors(admin_user: str = Depends(get_current_admin_user)):
    """Clear all errors from the log."""
    _error_log.clear()
    return {"message": "Error log cleared"}


@router.get("/export")
async def export_errors(
    format: str = "json",
    admin_user: str = Depends(get_current_admin_user),
):
    """Export errors in specified format."""
    cleanup_old_errors()

    if format == "json":
        return {
            "errors": _error_log,
            "exported_at": datetime.now().isoformat(),
            "total": len(_error_log),
        }
    elif format == "csv":
        # Simple CSV format
        lines = ["timestamp,error_type,message,severity"]
        for error in _error_log:
            lines.append(
                f"{error['timestamp']},{error['error_type']},{error['message']},{error['severity']}"
            )
        return {"csv": "\n".join(lines)}
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Unsupported format: {format}"}
        )
