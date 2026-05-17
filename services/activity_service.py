#!/usr/bin/env python3

"""
SvxLink activity parser.

Extracts operator-facing reflector talker activity from svxlink.log.
"""

import re
from services.log_service import get_svxlink_log_path

LOG_FILE = get_svxlink_log_path()


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
    active_row_marked = False

    for line in reversed(lines):

        match = talker_re.search(line)

        if not match:
                continue

        state = match.group("state")

        is_active = False

        if state == "start" and not active_row_marked:
            is_active = True
            active_row_marked = True

        activity.append({
            "time": match.group("time"),
            "callsign": match.group("callsign"),
            "tg": match.group("tg"),
            "m": "ACTIVE" if state == "start" else "OFF",
            "a": "SVXRef",
            "name": "------",
            "active": is_active,
        })

        if len(activity) >= limit:
            break

    return activity