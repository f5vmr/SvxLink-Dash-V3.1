#!/usr/bin/env python3

"""
Prepare the Raspberry Pi GPIO selection map.
"""

import sys
from pathlib import Path


DASHBOARD_ROOT = Path(__file__).resolve().parents[1]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from services.gpio_service import prepare_gpio_lines


def main():
    data = prepare_gpio_lines(
        "raspberry_pi",
        force=True,
    )

    line_count = sum(
        len(chip.get("lines", []))
        for chip in data.get("gpiochips", [])
    )

    print(
        f"Wrote {line_count} GPIO choices "
        "to /opt/dashboard/config/gpio_lines.json"
    )


if __name__ == "__main__":
    main()