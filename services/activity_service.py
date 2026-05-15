#!/usr/bin/env python3

"""
SvxLink activity parser.

Extracts operator-facing reflector activity from svxlink.log.
"""

from pathlib import Path
import re


LOG_FILE = Path("/var/log/svxlink.log")


def get_reflector_activity(limit=10):
    """
    Return recent reflector activity entries.

    Initial parser is deliberately conservative.
    Unknown fields are filled with dashes.
    """

    if not LOG_FILE.exists():
        return []

    try:
        lines = LOG_FILE.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()

    except Exception:
        return []

    activity = []

    # Example patterns will be refined against your actual log format.
    callsign_re = re.compile(r"\b([A-Z0-9]{2,}[A-Z0-9/-]*)\b")
    tg_re = re.compile(r"\bTG[# ]*([0-9]+)\b|talkgroup[: ]+([0-9]+)", re.IGNORECASE)
    time_re = re.compile(r"\b([0-9]{2}:[0-9]{2}:[0-9]{2})\b")

    for line in reversed(lines):

        if "Reflector" not in line and "TG" not in line and "talkgroup" not in line.lower():
            continue

        time_match = time_re.search(line)
        tg_match = tg_re.search(line)
        call_match = callsign_re.search(line)

        tg = "-"
        if tg_match:
            tg = tg_match.group(1) or tg_match.group(2)

        activity.append({
            "time": time_match.group(1) if time_match else "-",
            "callsign": call_match.group(1) if call_match else "-",
            "tg": tg,
            "m": "OFF",
            "a": "SVXRef",
            "name": "------",
        })

        if len(activity) >= limit:
            break

    return activity