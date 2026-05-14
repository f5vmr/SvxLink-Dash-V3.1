#!/usr/bin/env python3

"""
Runtime monitoring helpers for SvxLink-Dash-V3.

Read-only status collection only.
No control functions belong here.
"""

from pathlib import Path
import subprocess
import time

from services.svxlink_service import svxlink_status

UPTIME_FILE = Path("/proc/uptime")


def get_system_uptime():
    """
    Return human-readable system uptime.
    """

    try:
        uptime_seconds = float(
            UPTIME_FILE.read_text().split()[0]
        )

    except Exception:
        return "unknown"

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    parts.append(f"{minutes}m")

    return " ".join(parts)


def get_connected_reflector():
    """
    Attempt to determine connected reflector.

    Initial implementation:
    parse svxlink log tail.

    This will evolve later.
    """

    log_file = Path("/var/log/svxlink.log")

    if not log_file.exists():
        return "unknown"

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception:
        return "unknown"

    lines.reverse()

    for line in lines[:200]:

        if "ReflectorLogic: Connected to" in line:
            return line.split("Connected to")[-1].strip()

    return "not connected"


def get_runtime_status(model):
    """
    Collect dashboard runtime information.
    """

    return {
        "callsign": model.get("node", {}).get(
            "callsign",
            "unknown"
        ),

        "node_type": model.get("node", {}).get(
            "type",
            "unknown"
        ),

        "service_status": svxlink_status(),

        "uptime": get_system_uptime(),

        "reflector": get_connected_reflector(),

        "modules": model.get("modules", {}).get(
            "enabled",
            []
        ),
        "recent_log": get_recent_log_lines(),
    }
    
    def get_recent_log_lines(limit=40):
        log_file = Path("/var/log/svxlink.log")

        if not log_file.exists():
            return []

        try:
            lines = log_file.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines()

        except Exception:
            return []

        return lines[-limit:]
    