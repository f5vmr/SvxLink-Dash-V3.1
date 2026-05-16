#!/usr/bin/env python3

"""
SvxLink activity parser.

Extracts operator-facing reflector talker activity from svxlink.log.
"""

from pathlib import Path
import re


LOG_FILE = Path("/var/log/svxlink.log")


def get_reflector_activity(limit=10):
    """
    Return recent reflector talker activity.

    Only parses lines such as:
    ReflectorLogic: Talker start on TG #53573: NWAG
    ReflectorLogic: Talker stop on TG #53573: NWAG

    Ignores:
    - Node joined
    - Node left
    - Selecting TG
    - MultiTx events
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

    talker_re = re.compile(
        r"^(?P<time>.+?): ReflectorLogic: Talker "
        r"(?P<state>start|stop) on TG #(?P<tg>[0-9]+): "
        r"(?P<callsign>[A-Z0-9/-]+)"
    )

    activity = []

    for line in reversed(lines):

        match = talker_re.search(line)

        if not match:
            continue

        state = match.group("state")

        activity.append({
            "time": match.group("time"),
            "callsign": match.group("callsign"),
            "tg": match.group("tg"),
            "m": "ACTIVE" if state == "start" else "OFF",
            "a": "SVXRef",
            "name": "------",
            "active": state == "start",
        })

        if len(activity) >= limit:
            break

    return activity