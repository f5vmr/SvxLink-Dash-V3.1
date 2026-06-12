#!/usr/bin/env python3

"""
DTMF control helper for {{ version_info.dashboard_name }}.

Writes DTMF command strings to the SvxLink control PTY selected
for the current node type.
"""

from pathlib import Path
import json
import re


NODE_MODEL = Path("/opt/dashboard/config/node_model.json")


def get_dtmf_control_path():
    """
    Return the DTMF control PTY path for the current node type.
    """

    try:
        model = json.loads(
            NODE_MODEL.read_text(encoding="utf-8")
        )
    except Exception:
        model = {}

    node_type = model.get("node", {}).get("type")

    if node_type == "repeater":
        return Path("/dev/shm/repeater_dtmf_ctrl")

    return Path("/dev/shm/simplex_dtmf_ctrl")


def validate_dtmf(command):
    """
    Allow only digits, star and hash.
    """

    return bool(re.fullmatch(r"[0-9*#]+", command))


def send_dtmf(command):
    """
    Send a DTMF command to SvxLink control PTY.
    """

    if not validate_dtmf(command):
        raise ValueError("Invalid DTMF command.")

    dtmf_path = get_dtmf_control_path()

    if not dtmf_path.exists():
        raise FileNotFoundError(
            f"DTMF control path not found: {dtmf_path}"
        )

    with dtmf_path.open("w", encoding="utf-8") as handle:
        handle.write(command)

    return command