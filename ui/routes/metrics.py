"""Health metrics and monitoring routes."""

import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from config.settings import get_settings
from providers.registry import ProviderRegistry
from ..auth import get_current_admin_user

router = APIRouter()

# Metrics storage (in-memory with time windows)
_request_metrics = deque(maxlen=3600)  # Last hour of requests
_error_metrics = deque(maxlen=3600)  # Last hour of errors
_provider_metrics = {}  # Provider-specific metrics


def record_request(
    provider_id: str,
    model_id: str,
    status: str,
    duration_ms: float,
) -> None:
    """Record a request metric."""
    _request_metrics.append({
        "timestamp": time.time(),
        "provider_id": provider_id,
        "model_id": model_id,
        "status": status,
        "duration_ms": duration_ms,
    })

    # Update provider metrics
    if provider_id not in _provider_metrics:
        _provider_metrics[provider_id] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
        }

    _provider_metrics[provider_id]["total_requests"] += 1
    _provider_metrics[provider_id]["total_duration_ms"] += duration_ms

    if status == "success":
        _provider_metrics[provider_id]["successful_requests"] += 1
    else:
        _provider_metrics[provider_id]["failed_requests"] += 1


def record_error(
    error_type: str,
    provider_id: str | None = None,
    message: str = "",
) -> None:
    """Record an error metric."""
    _error_metrics.append({
        "timestamp": time.time(),
        "error_type": error_type,
        "provider_id": provider_id,
        "message": message,
    })


@router.get("/overview")
async def get_metrics_overview(
    admin_user: str = Depends(get_current_admin_user),
):
    """Get metrics overview for the last hour."""
    current_time = time.time()
    one_hour_ago = current_time - 3600

    # Filter metrics for last hour
    recent_requests = [m for m in _request_metrics if m["timestamp"] >= one_hour_ago]
    recent_errors = [m for m in _error_metrics if m["timestamp"] >= one_hour_ago]

    # Calculate statistics
    total_requests = len(recent_requests)
    successful_requests = len([m for m in recent_requests if m["status"] == "success"])
    failed_requests = total_requests - successful_requests

    # Calculate average duration
    avg_duration = 0
    if recent_requests:
        total_duration = sum(m["duration_ms"] for m in recent_requests)
        avg_duration = total_duration / len(recent_requests)

    # Calculate requests per minute
    requests_per_minute = total_requests / 60 if total_requests > 0 else 0

    # Calculate error rate
    error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

    return {
        "period": "1 hour",
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2),
        "error_rate": round(error_rate, 2),
        "avg_duration_ms": round(avg_duration, 2),
        "requests_per_minute": round(requests_per_minute, 2),
        "total_errors": len(recent_errors),
    }


@router.get("/providers")
async def get_provider_metrics(
    admin_user: str = Depends(get_current_admin_user),
):
    """Get provider-specific metrics."""
    current_time = time.time()
    one_hour_ago = current_time - 3600

    # Filter metrics for last hour
    recent_requests = [m for m in _request_metrics if m["timestamp"] >= one_hour_ago]

    # Group by provider
    provider_stats = {}
    for metric in recent_requests:
        provider_id = metric["provider_id"]
        if provider_id not in provider_stats:
            provider_stats[provider_id] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration_ms": 0,
            }

        provider_stats[provider_id]["total_requests"] += 1
        provider_stats[provider_id]["total_duration_ms"] += metric["duration_ms"]

        if metric["status"] == "success":
            provider_stats[provider_id]["successful_requests"] += 1
        else:
            provider_stats[provider_id]["failed_requests"] += 1

    # Calculate averages
    for provider_id, stats in provider_stats.items():
        if stats["total_requests"] > 0:
            stats["avg_duration_ms"] = round(stats["total_duration_ms"] / stats["total_requests"], 2)
            stats["success_rate"] = round((stats["successful_requests"] / stats["total_requests"] * 100), 2)
        else:
            stats["avg_duration_ms"] = 0
            stats["success_rate"] = 0

    return {"providers": provider_stats}


@router.get("/timeline")
async def get_metrics_timeline(
    interval: int = 60,  # seconds
    points: int = 60,  # number of data points
    admin_user: str = Depends(get_current_admin_user),
):
    """Get metrics timeline for graphing."""
    current_time = time.time()
    start_time = current_time - (interval * points)

    # Create time buckets
    buckets = {}
    for i in range(points):
        bucket_time = start_time + (i * interval)
        buckets[bucket_time] = {
            "timestamp": bucket_time,
            "requests": 0,
            "errors": 0,
        }

    # Fill buckets
    for metric in _request_metrics:
        if metric["timestamp"] >= start_time:
            bucket_index = int((metric["timestamp"] - start_time) / interval)
            if bucket_index < points:
                bucket_time = start_time + (bucket_index * interval)
                if bucket_time in buckets:
                    buckets[bucket_time]["requests"] += 1

    for metric in _error_metrics:
        if metric["timestamp"] >= start_time:
            bucket_index = int((metric["timestamp"] - start_time) / interval)
            if bucket_index < points:
                bucket_time = start_time + (bucket_index * interval)
                if bucket_time in buckets:
                    buckets[bucket_time]["errors"] += 1

    # Convert to sorted list
    timeline = sorted(buckets.values(), key=lambda x: x["timestamp"])

    return {
        "interval": interval,
        "points": points,
        "timeline": timeline,
    }


@router.get("/errors")
async def get_error_metrics(
    limit: int = 100,
    admin_user: str = Depends(get_current_admin_user),
):
    """Get recent error metrics."""
    current_time = time.time()
    one_hour_ago = current_time - 3600

    # Filter errors for last hour
    recent_errors = [m for m in _error_metrics if m["timestamp"] >= one_hour_ago]

    # Limit results
    recent_errors = recent_errors[-limit:] if len(recent_errors) > limit else recent_errors

    # Reverse to show newest first
    recent_errors.reverse()

    # Convert timestamps to ISO format
    for error in recent_errors:
        error["timestamp_iso"] = datetime.fromtimestamp(error["timestamp"]).isoformat()

    return {
        "errors": recent_errors,
        "total": len(_error_metrics),
    }


@router.post("/reset")
async def reset_metrics(admin_user: str = Depends(get_current_admin_user)):
    """Reset all metrics."""
    _request_metrics.clear()
    _error_metrics.clear()
    _provider_metrics.clear()
    return {"message": "Metrics reset"}
