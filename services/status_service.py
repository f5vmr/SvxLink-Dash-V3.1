#!/usr/bin/env python3

"""
Runtime monitoring helpers for {{ version_info.dashboard_name }}.

Read-only status collection only.
No control functions belong here.
"""

from pathlib import Path
import subprocess
import time
import re 
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
    Determine reflector connection state from recent SvxLink log lines.

    The latest relevant ReflectorLogic event wins.
    """

    log_file = get_svxlink_log_path()

    reflector_name = "Connected"

    if model:
        reflector_name = (
            model.get("reflector", {})
            .get("name", "Connected")
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

    connected_terms = (
        "authentication ok",
        "connected to",
        "connection established",
        "reflector connected",
    )

    disconnected_terms = (
        "disconnected",
        "connection failed",
        "connection lost",
        "server closed connection",
        "authentication failed",
    )

    for line in reversed(lines[-800:]):

        lower = line.lower()

        if "reflectorlogic" not in lower:
            continue

        if any(term in lower for term in disconnected_terms):
            return "not connected"

        if any(term in lower for term in connected_terms):
            return reflector_name

    return "not connected"

def get_radio_state(selected_port="1"):
        """
        Determine current radio state from recent SvxLink log lines.
    
        TX state is detected from either Tx1 messages.
        RX/input state is detected from Rx1 squelch messages.
        """

        log_file = get_svxlink_log_path()

        tx_active = False
        rx_open = False
        selected_port = str(selected_port or "1")
        rx_name = f"rx{selected_port}:"
        tx_name = f"tx{selected_port}:"

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
            if tx_name not in lower:
                continue
            if "turning the transmitter off" in lower:
                tx_active = False
                break
            if "turning the transmitter on" in lower:
                tx_active = True
                break

        for line in reversed(lines[-300:]):
            lower = line.lower()

            if f"{rx_name} the squelch is closed" in lower:
                rx_open = False
                break

            if f"{rx_name} the squelch is open" in lower:
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
def get_active_talkgroup():
    """
    Determine the currently selected SvxReflector talkgroup
    from recent SvxLink log lines.

    Examples:
        ReflectorLogic: Selecting TG #0   -> Standby
        ReflectorLogic: Selecting TG #505 -> 505
    """

    log_file = get_svxlink_log_path()

    if not log_file.exists():
        return "Unknown"

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception:
        return "Unknown"

    tg_pattern = re.compile(
        r"ReflectorLogic:\s+Selecting TG #(\d+)"
    )

    for line in reversed(lines[-1000:]):
        match = tg_pattern.search(line)

        if not match:
            continue

        talkgroup = match.group(1)

        if talkgroup == "0":
            return "Standby"

        return talkgroup

    return "Standby"
def get_status_callsign(model, selected_port="1"):
    """
    Return the callsign for the selected dashboard port.
    """

    selected_port = str(selected_port or "1")

    port_node = (
        model.get("nodes", {})
        .get(selected_port, {})
    )

    return (
        port_node.get("callsign")
        or model.get("node", {}).get("callsign")
        or model.get("ident", {}).get("callsign")
        or "unknown"
    )
def get_runtime_status(model, selected_port="1"):
    """
    Collect dashboard runtime information.
    """

    selected_port = str(selected_port or "1")

    return {
        "callsign": get_status_callsign(
            model,
            selected_port=selected_port,
        ),

        "node_type": model.get("nodes", {})
        .get(selected_port, {})
        .get(
            "role",
            model.get("node", {}).get(
                "type",
                "unknown"
            )
        ),

        "service_status": svxlink_status(),

        "uptime": get_system_uptime(),

        "reflector": get_connected_reflector(model),

        "active_talkgroup": get_active_talkgroup(),

        "modules": model.get("nodes", {})
        .get(selected_port, {})
        .get("modules", model.get("modules", {}))
        .get(
            "enabled",
            []
        ),

        "recent_log": get_recent_log_lines(),
        "selected_port": selected_port,
        "radio_state": get_radio_state(selected_port=selected_port),
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
