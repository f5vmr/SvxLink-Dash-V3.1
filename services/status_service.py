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
from services.log_service import get_svxlink_log_path

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


def get_connected_reflector(model=None):
    """
    Determine reflector connection state.
    """

    log_file = get_svxlink_log_path()

    reflector_name = "Unknown"

    if model:
        reflector_name = (
            model.get("reflector", {})
            .get("name", "Unknown")
        )

    if not log_file.exists():
        return "unknown"

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception:
        return "unknown"

    for line in reversed(lines[-500:]):

        lower = line.lower()

        if "reflectorlogic" not in lower:
            continue

        if (
            "disconnected" in lower
            or "connection failed" in lower
        ):
            return "not connected"

        if "authentication ok" in lower:
            return f"Connected ({reflector_name})"

    return "not connected"

def get_radio_state():
        """
        Determine current radio state from recent SvxLink log lines.
    
        TX state is detected from either Tx1 or MultiTx messages.
        RX/input state is detected from Rx1 squelch messages.
        """

        log_file = get_svxlink_log_path()

        tx_active = False
        rx_open = False

        if not log_file.exists():
            return {
                "label": "Listening",
                "input": "Unknown",
                "class": "radio-standby",
                "tx": False,
                "rx": False,
            }

        try:
            lines = log_file.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines()

        except Exception:
            return {
                "label": "Listening",
                "input": "Unknown",
                "class": "radio-standby",
                "tx": False,
                "rx": False,
            }

        for line in reversed(lines[-300:]):
            lower = line.lower()

            if "turning the transmitter off" in lower:
                tx_active = False
                break

            if "turning the transmitter on" in lower:
                tx_active = True
                break

        for line in reversed(lines[-300:]):
            lower = line.lower()

            if "rx1: the squelch is closed" in lower:
                rx_open = False
                break

            if "rx1: the squelch is open" in lower:
                rx_open = True
                break

        if tx_active:
            label = "Transmitting"
            css_class = "radio-tx"
        elif rx_open:
            label = "Receiving"
            css_class = "radio-rx"
        else:
            label = "Listening"
            css_class = "radio-standby"

        return {
            "label": label,
            "input": "Open" if rx_open else "Closed",
            "class": css_class,
            "tx": tx_active,
            "rx": rx_open,
    }
def get_echolink_state():
    """
    Determine current EchoLink activity from recent SvxLink log lines.
    """

    log_file = get_svxlink_log_path()

    if not log_file.exists():
        return {
            "active": False,
            "label": "Idle",
            "station": "",
            "class": "status-good",
        }

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception:
        return {
            "active": False,
            "label": "Unknown",
            "station": "",
            "class": "status-warn",
        }

    for line in reversed(lines[-500:]):

        if "EchoLink: no connected stations" in line:
            return {
                "active": False,
                "label": "Idle",
                "station": "",
                "class": "status-good",
            }

        if "EchoLink: single connected station =" in line:
            station = line.split("=", 1)[-1].strip()

            return {
                "active": True,
                "label": "Connected",
                "station": station,
                "class": "status-warn",
            }

    return {
        "active": False,
        "label": "Idle",
        "station": "",
        "class": "status-good",
    }    
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

        "reflector": get_connected_reflector(model),

        "modules": model.get("modules", {}).get(
            "enabled",
            []
        ),
        "recent_log": get_recent_log_lines(),
        
        "radio_state": get_radio_state(),
        "echolink_state": get_echolink_state(),
    }
def get_recent_log_lines(limit=40):
    """
    Return recent SvxLink log lines for dashboard display.
    """

    log_file = get_svxlink_log_path()

    if not log_file.exists():
        return ["Log file not found: /var/log/svxlink.log"]

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception as exc:
        return [f"Unable to read log file: {exc}"]

    return lines[-limit:]    
