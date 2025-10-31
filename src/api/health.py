import logging
import os
import sys
import psutil
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Armazena o timestamp de quando o serviço iniciou
SERVICE_START_TIME = datetime.now(timezone.utc)


async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint with detailed system information.

    Returns:
        Dict containing detailed service health and system metrics
    """
    logger.info("Comprehensive health check requested")

    current_time = datetime.now(timezone.utc)
    uptime_seconds = (current_time - SERVICE_START_TIME).total_seconds()

    # System metrics
    process = psutil.Process()
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent(interval=0.1)

    return {
        "status": "healthy",
        "timestamp": current_time.isoformat(),
        "uptime": {
            "seconds": uptime_seconds,
            "formatted": _format_uptime(uptime_seconds),
            "started_at": SERVICE_START_TIME.isoformat(),
        },
        "service": {
            "name": "notion-webhook-api",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "description": "Notion webhook integration service",
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "process_id": os.getpid(),
        },
        "resources": {
            "memory": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2),
            },
            "cpu": {"percent": round(cpu_percent, 2), "cores": psutil.cpu_count()},
            "disk": {"usage_percent": round(psutil.disk_usage("/").percent, 2)},
        },
    }


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
