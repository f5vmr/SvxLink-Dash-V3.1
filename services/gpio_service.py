#!/usr/bin/env python3

"""
GPIO line helper for {{ version_info.dashboard_name }}.
"""

import json
from pathlib import Path


GPIO_LINES_FILE = Path("/opt/dashboard/config/gpio_lines.json")


def load_gpio_lines():
    """
    Load scanned GPIO line map.
    """

    if not GPIO_LINES_FILE.exists():
        return {
            "gpiochips": []
        }

    try:
        return json.loads(
            GPIO_LINES_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "gpiochips": []
        }


def flatten_gpio_lines():
    """
    Return GPIO lines as a simple list for templates.
    """

    data = load_gpio_lines()
    rows = []

    for chip in data.get("gpiochips", []):
        chip_name = chip.get("chip", "")

        for line in chip.get("lines", []):
            rows.append({
                "chip": line.get("chip", chip_name),
                "line": line.get("line"),
                "label": line.get("label", ""),
                "available": line.get("available", True),
            })

    return rows