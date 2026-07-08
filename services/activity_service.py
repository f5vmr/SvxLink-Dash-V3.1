#!/usr/bin/env python3

"""
SvxLink activity parser.

Extracts operator-facing reflector talker activity from svxlink.log.
"""

import re
from datetime import datetime, timezone

from services.log_service import get_svxlink_log_path

LOG_FILE = get_svxlink_log_path()

ACTIVE_TIMEOUT_SECONDS = 10


def _parse_log_time(value):
    """
    Parse SvxLink log timestamp.

    Example:
    Wed Jul  8 14:11:44 2026
    """

    try:
        return datetime.strptime(value.strip(), "%a %b %d %H:%M:%S %Y").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        return None


def get_reflector_activity(limit=10):
    """
    Return latest reflector talker state per callsign/TG.

    This intentionally collapses repeated start/stop pairs so the dashboard
    does not show multiple rows for the same recent station.
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
    seen = set()
    now = datetime.now(timezone.utc)

    for line in reversed(lines):
        match = talker_re.search(line)

        if not match:
            continue

        callsign = match.group("callsign")
        tg = match.group("tg")
        key = (callsign, tg)

        # We are reading newest first, so the first event for this callsign/TG
        # is the current/latest state. Ignore older matching start/stop pairs.
        if key in seen:
            continue

        seen.add(key)

        state = match.group("state")
        log_time = match.group("time")
        log_dt = _parse_log_time(log_time)

        is_recent = False
        if log_dt is not None:
            age = (now - log_dt).total_seconds()
            is_recent = 0 <= age <= ACTIVE_TIMEOUT_SECONDS

        is_active = state == "start" and is_recent

        activity.append({
            "time": log_time,
            "callsign": callsign,
            "tg": tg,
            "m": "ACTIVE" if is_active else "OFF",
            "a": "SVXRef",
            "active": is_active,
        })

        if len(activity) >= limit:
            break

    return activity