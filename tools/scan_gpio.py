#!/usr/bin/env python3

"""
Scan available GPIO lines for SvxLink-Dash-V3.

Currently provides a Raspberry Pi focused GPIO list:
gpiochip0, GPIO2-GPIO27.
"""

import json
from pathlib import Path


OUTPUT_FILE = Path("/opt/dashboard/config/gpio_lines.json")


def build_raspberry_pi_gpio_lines():
    lines = []

    for line in range(2, 28):
        lines.append({
            "chip": "gpiochip0",
            "line": line,
            "label": f"GPIO{line}",
            "available": True,
        })

    return {
        "platform": "raspberry_pi",
        "gpiochips": [
            {
                "chip": "gpiochip0",
                "label": "Raspberry Pi GPIO",
                "lines": lines,
            }
        ],
    }


def main():
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = build_raspberry_pi_gpio_lines()

    OUTPUT_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )

    print(f"Wrote GPIO line map to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()