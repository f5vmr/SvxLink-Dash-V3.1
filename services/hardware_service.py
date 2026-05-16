#!/usr/bin/env python3

"""
Hardware/system telemetry helpers.
"""

from pathlib import Path
import os
import platform
import socket
import subprocess


def read_first_line(path):
    try:
        return Path(path).read_text().strip().splitlines()[0]
    except Exception:
        return "unknown"


def get_ip_address():
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            text=True,
            capture_output=True,
        )
        return result.stdout.strip().split()[0]
    except Exception:
        return "unknown"


def get_cpu_temp():
    temp_path = Path("/sys/class/thermal/thermal_zone0/temp")

    try:
        raw = int(temp_path.read_text().strip())
        return f"{raw / 1000:.1f}°C"
    except Exception:
        return "unknown"


def get_disk_usage():
    try:
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        percent = int((used / total) * 100)
        return f"{percent}%"
    except Exception:
        return "unknown"


def get_memory_usage():
    try:
        data = Path("/proc/meminfo").read_text().splitlines()
        values = {}

        for line in data:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])

        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)

        if not total:
            return "unknown"

        used = total - available
        percent = int((used / total) * 100)

        return f"{percent}%"
    except Exception:
        return "unknown"


def get_system_info():
    return {
        "hostname": socket.gethostname(),
        "ip": get_ip_address(),
        "kernel": platform.release(),
        "os": read_first_line("/etc/os-release").replace("PRETTY_NAME=", "").replace('"', ""),
        "cpu_temp": get_cpu_temp(),
        "disk": get_disk_usage(),
        "memory": get_memory_usage(),
    }