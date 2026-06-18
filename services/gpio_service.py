#!/usr/bin/env python3

"""
GPIO line helper for {{ version_info.dashboard_name }}.
"""

import json
import subprocess
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
def scan_gpio_lines():
    """
    Scan current GPIO chips and lines using gpioinfo.

    Returns data suitable for saving to GPIO_LINES_FILE.
    """

    result = subprocess.run(
        ["gpioinfo"],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "gpioinfo failed: "
            + (result.stderr.strip() or result.stdout.strip())
        )

    gpiochips = []
    current_chip = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip()

        if line.startswith("gpiochip"):
            chip_name = line.split()[0].rstrip(":")

            current_chip = {
                "chip": chip_name,
                "lines": [],
            }

            gpiochips.append(current_chip)
            continue

        if current_chip is None:
            continue

        stripped = line.strip()

        if not stripped.startswith("line "):
            continue

        try:
            before_colon, after_colon = stripped.split(":", 1)
        except ValueError:
            continue

        parts = before_colon.split()

        if len(parts) < 2:
            continue

        try:
            line_number = int(parts[1])
        except ValueError:
            continue

        quoted = []
        remainder = after_colon

        while '"' in remainder:
            before, quote, rest = remainder.partition('"')
            value, quote, remainder = rest.partition('"')
            quoted.append(value)

        label = quoted[0] if len(quoted) >= 1 else ""
        consumer = quoted[1] if len(quoted) >= 2 else ""

        available = "unused" in after_colon

        direction = ""
        if " input " in f" {after_colon} ":
            direction = "input"
        elif " output " in f" {after_colon} ":
            direction = "output"

        active = ""
        if "active-high" in after_colon:
            active = "active-high"
        elif "active-low" in after_colon:
            active = "active-low"

        current_chip["lines"].append({
            "chip": current_chip["chip"],
            "line": line_number,
            "label": label,
            "consumer": consumer,
            "direction": direction,
            "active": active,
            "available": available,
        })

    return {
        "gpiochips": gpiochips
    }


def save_gpio_lines(data):
    """
    Save scanned GPIO line map.
    """

    GPIO_LINES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    GPIO_LINES_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def refresh_gpio_lines():
    """
    Scan and save the current GPIO line map.
    """

    data = scan_gpio_lines()
    save_gpio_lines(data)
    return data


def find_gpio_line(label, data=None):
    """
    Find one GPIO line by stable gpio-line-name.

    Returns:
        {
            "chip": "gpiochip3",
            "line": "RX_1",
            "offset": 6,
            "consumer": "...",
            "available": true/false,
        }

    or None if not found.
    """

    if data is None:
        data = load_gpio_lines()

    for chip in data.get("gpiochips", []):
        chip_name = chip.get("chip", "")

        for line in chip.get("lines", []):
            if line.get("label") == label:
                return {
                    "chip": line.get("chip", chip_name),
                    "line": label,
                    "offset": line.get("line"),
                    "consumer": line.get("consumer", ""),
                    "direction": line.get("direction", ""),
                    "active": line.get("active", ""),
                    "available": line.get("available", True),
                }

    return None


def discover_named_gpio_lines(labels, refresh=True):
    """
    Discover multiple stable GPIO line names.

    By default this refreshes gpio_lines.json first.
    """

    data = refresh_gpio_lines() if refresh else load_gpio_lines()

    resolved = {}
    missing = []

    for label in labels:
        found = find_gpio_line(label, data)

        if found:
            resolved[label] = found
        else:
            missing.append(label)

    return resolved, missing


def required_ics_gpio_lines(model):
    """
    Return the GPIO line names required by the selected ICS profile.
    """

    hardware = model.get("hardware", {})

    profile_id = (
        model.get("hardware_profile_id")
        or hardware.get("profile_id")
        or hardware.get("id")
    )

    enabled_ports = model.get("ports", {}).get("enabled", [])

    labels = []

    for port in enabled_ports:
        port_id = str(port)
        labels.append(f"RX_{port_id}")
        labels.append(f"TX_{port_id}")

    if profile_id in ("ics_4x", "ics_8x"):
        labels.append("PCM_PDWN")

    return labels


def update_model_gpiod_discovery(model):
    """
    Refresh GPIO discovery and store resolved GPIOD data in node_model.
    """

    labels = required_ics_gpio_lines(model)

    resolved, missing = discover_named_gpio_lines(
        labels,
        refresh=True,
    )

    model.setdefault("gpiod", {})
    model["gpiod"]["resolved_lines"] = resolved
    model["gpiod"]["missing_lines"] = missing

    nodes = model.get("nodes", {})

    for port in model.get("ports", {}).get("enabled", []):
        port_id = str(port)
        node = nodes.get(port_id, {})

        rx_label = f"RX_{port_id}"
        tx_label = f"TX_{port_id}"

        rx = resolved.get(rx_label, {})
        tx = resolved.get(tx_label, {})

        node.setdefault("gpio", {})

        node["gpio"]["cos_chip"] = rx.get("chip", "")
        node["gpio"]["cos_line"] = rx.get("line", rx_label)
        node["gpio"]["cos_offset"] = rx.get("offset")

        node["gpio"]["ptt_chip"] = tx.get("chip", "")
        node["gpio"]["ptt_line"] = tx.get("line", tx_label)
        node["gpio"]["ptt_offset"] = tx.get("offset")

        nodes[port_id] = node

    model["nodes"] = nodes

    return model