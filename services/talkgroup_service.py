#!/usr/bin/env python3

"""
Talkgroup configuration helpers for SvxLink-Dash-V3.
"""

from pathlib import Path
import json

from data.talkgroups import TALKGROUPS


CONFIG_DIR = Path("/opt/dashboard/config")

TALKGROUP_FILE = CONFIG_DIR / "talkgroups.json"


def ensure_config_dir():
    """
    Ensure config directory exists.
    """

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_talkgroups(environment):
    """
    Load talkgroups from local JSON override if present.

    Falls back to built-in defaults.
    """

    ensure_config_dir()

    if TALKGROUP_FILE.exists():

        try:
            data = json.loads(
                TALKGROUP_FILE.read_text(
                    encoding="utf-8"
                )
            )

            return data.get(
                environment,
                TALKGROUPS.get(environment, [])
            )

        except Exception:
            pass

    return TALKGROUPS.get(environment, [])


def save_talkgroups(environment, talkgroups):
    """
    Save talkgroups to local JSON config.
    """

    ensure_config_dir()

    data = {}

    if TALKGROUP_FILE.exists():

        try:
            data = json.loads(
                TALKGROUP_FILE.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            data = {}

    data[environment] = talkgroups

    TALKGROUP_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )

    return TALKGROUP_FILE