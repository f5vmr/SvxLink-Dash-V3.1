import subprocess
from typing import Dict, List


def run_cmd(cmd: List[str], timeout: int = 20) -> Dict[str, str]:
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )

    return {
        "command": " ".join(cmd),
        "returncode": str(result.returncode),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def get_svxlink_service_state() -> Dict[str, str]:
    return run_cmd(["systemctl", "is-active", "svxlink.service"])


def stop_svxlink_for_calibration() -> Dict[str, str]:
    return run_cmd(["sudo", "systemctl", "stop", "svxlink.service"])


def restart_svxlink_after_calibration() -> Dict[str, str]:
    return run_cmd(["sudo", "systemctl", "restart", "svxlink.service"])


def run_devcal_test(amplitude: str, frequency: str, duration: str) -> Dict[str, str]:
    # Placeholder until we confirm the exact devcal command syntax in use.
    cmd = ["sudo", "devcal"]

    if amplitude:
        cmd.extend(["--amplitude", amplitude])

    if frequency:
        cmd.extend(["--frequency", frequency])

    if duration:
        cmd.extend(["--duration", duration])

    return run_cmd(cmd, timeout=60)
