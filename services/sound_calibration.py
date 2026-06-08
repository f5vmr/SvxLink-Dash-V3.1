#!/usr/bin/env python3

import subprocess
from typing import Any, Dict, List


SVXLINK_SERVICE = "svxlink.service"


def run_cmd(cmd: List[str], timeout: int = 30) -> Dict[str, Any]:
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )

    return {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def get_svxlink_service_state() -> Dict[str, Any]:
    return run_cmd(["systemctl", "is-active", SVXLINK_SERVICE], timeout=10)


def stop_svxlink_for_calibration() -> Dict[str, Any]:
    return run_cmd(["sudo", "systemctl", "stop", SVXLINK_SERVICE], timeout=20)


def restart_svxlink_after_calibration() -> Dict[str, Any]:
    return run_cmd(["sudo", "systemctl", "restart", SVXLINK_SERVICE], timeout=30)