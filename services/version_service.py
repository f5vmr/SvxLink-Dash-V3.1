#!/usr/bin/env python3

"""
Version helpers for SvxLink-Dash-V3.
"""

import subprocess


DASHBOARD_VERSION = "3.0"


def get_dashboard_version():
    return DASHBOARD_VERSION


def get_svxlink_package_version():
    try:
        result = subprocess.run(
            [
                "/usr/bin/dpkg-query",
                "-W",
                "-f=${Version}",
                "svxlink",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        return result.stdout.strip() or "unknown"

    except Exception:
        return "unknown"


def get_svxlink_engine_version():
    try:
        result = subprocess.run(
            [
                "/usr/bin/svxlink",
                "--version",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        first_line = result.stdout.strip().splitlines()[0]
        return first_line.replace("SvxLink", "").strip()

    except Exception:
        return "unknown"


def get_version_info():
    return {
        "dashboard": get_dashboard_version(),
        "package": get_svxlink_package_version(),
        "engine": get_svxlink_engine_version(),
    }