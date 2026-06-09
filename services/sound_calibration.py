#!/usr/bin/env python3

from pathlib import Path
from typing import Any, Dict, List

import os
import shlex
import signal
import stat
import subprocess


SVXLINK_SERVICE = "svxlink.service"

DEVCAL_LOG = Path("/tmp/svxlink-devcal.log")
DEVCAL_PID = Path("/tmp/svxlink-devcal.pid")
DEVCAL_MODE = Path("/tmp/svxlink-devcal.mode")
DEVCAL_INPUT = Path("/tmp/svxlink-devcal.in")
DEVCAL_TX_STATE = Path("/tmp/svxlink-devcal.tx")


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
    return run_cmd(
        ["/usr/bin/systemctl", "is-active", SVXLINK_SERVICE],
        timeout=10,
    )


def stop_svxlink_for_calibration() -> Dict[str, Any]:
    return run_cmd(
        ["sudo", "/usr/bin/systemctl", "stop", SVXLINK_SERVICE],
        timeout=20,
    )


def restart_svxlink_after_calibration() -> Dict[str, Any]:
    return run_cmd(
        ["sudo", "/usr/bin/systemctl", "restart", SVXLINK_SERVICE],
        timeout=30,
    )


def prepare_devcal_input_pipe() -> None:
    if DEVCAL_INPUT.exists():
        try:
            mode = DEVCAL_INPUT.stat().st_mode

            if stat.S_ISFIFO(mode):
                os.chmod(DEVCAL_INPUT, 0o666)
                return

            DEVCAL_INPUT.unlink()

        except FileNotFoundError:
            pass

    os.mkfifo(DEVCAL_INPUT, 0o666)
    os.chmod(DEVCAL_INPUT, 0o666)


def build_devcal_command(
    config_file: str,
    section: str,
    mode: str,
    modfqs: str,
    caldev: str,
    maxdev: str,
    headroom: str,
    audiodev: str = "",
    flat: bool = False,
    wide: bool = False,
) -> List[str]:
    config_file = (config_file or "/etc/svxlink/svxlink.conf").strip()
    section = (section or "").strip()
    mode = (mode or "").strip()

    if not section:
        raise ValueError("No SvxLink Tx/Rx section selected.")

    cmd = [
        "sudo",
        "/usr/bin/devcal",
    ]

    if mode == "txcal":
        # Known-good TX devcal mode is the interactive default.
        # Do not add --txcal here.
        pass

    elif mode == "rxcal":
        cmd.append("--rxcal")

    elif mode == "measure":
        cmd.append("--measure")

    else:
        raise ValueError("Invalid devcal mode selected.")

    # Keep options before the positional config file and section.
    if modfqs:
        cmd.append(f"--modfqs={modfqs}")

    if caldev:
        cmd.append(f"--caldev={caldev}")

    if maxdev:
        cmd.append(f"--maxdev={maxdev}")

    if headroom:
        cmd.append(f"--headroom={headroom}")

    if audiodev:
        cmd.append(f"--audiodev={audiodev}")

    if flat:
        cmd.append("--flat")

    if wide:
        cmd.append("--wide")

    cmd.extend([
        config_file,
        section,
    ])

    return cmd


def devcal_is_running() -> bool:
    if not DEVCAL_PID.exists():
        return False

    try:
        pid = int(DEVCAL_PID.read_text().strip())
        os.kill(pid, 0)
        return True

    except Exception:
        return False


def get_devcal_mode() -> str:
    if not DEVCAL_MODE.exists():
        return ""

    try:
        return DEVCAL_MODE.read_text(
            encoding="utf-8",
            errors="ignore",
        ).strip()

    except Exception:
        return ""


def get_devcal_tx_state() -> str:
    if not DEVCAL_TX_STATE.exists():
        return "off"

    try:
        state = DEVCAL_TX_STATE.read_text(
            encoding="utf-8",
            errors="ignore",
        ).strip().lower()

    except Exception:
        return "off"

    if state == "on":
        return "on"

    return "off"


def set_devcal_tx_state(state: str) -> None:
    state = "on" if state == "on" else "off"
    DEVCAL_TX_STATE.write_text(state, encoding="utf-8")


def toggle_devcal_tx_state() -> str:
    current = get_devcal_tx_state()
    new_state = "off" if current == "on" else "on"
    set_devcal_tx_state(new_state)
    return new_state


def _devcal_supervisor_code() -> str:
    return r'''
import os
import pty
import select
import signal
import subprocess
import sys
import time

fifo_path = sys.argv[1]
log_path = sys.argv[2]
cmd = sys.argv[3:]

running = True

def handle_signal(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

master_fd, slave_fd = pty.openpty()

with open(log_path, "a", encoding="utf-8", errors="ignore") as log:
    log.write("\nPTY supervisor starting devcal:\n")
    log.write(" ".join(cmd) + "\n\n")
    log.flush()

    process = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        start_new_session=True,
    )

    os.close(slave_fd)

    # Open FIFO read/write non-blocking so dashboard writers do not block
    # when no separate reader is waiting.
    fifo_fd = os.open(fifo_path, os.O_RDWR | os.O_NONBLOCK)

    try:
        while running:
            if process.poll() is not None:
                log.write("\ndevcal exited with return code %s\n" % process.returncode)
                log.flush()
                break

            readable, _, _ = select.select(
                [master_fd, fifo_fd],
                [],
                [],
                0.25,
            )

            if master_fd in readable:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    data = b""

                if data:
                    text = data.decode("utf-8", errors="replace")
                    log.write(text)
                    log.flush()

            if fifo_fd in readable:
                try:
                    data = os.read(fifo_fd, 4096)
                except BlockingIOError:
                    data = b""

                if data:
                    os.write(master_fd, data)

    finally:
        try:
            os.close(fifo_fd)
        except OSError:
            pass

        try:
            os.close(master_fd)
        except OSError:
            pass

        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except Exception:
                pass

            time.sleep(0.5)

            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except Exception:
                    pass
'''


def start_devcal_session(
    config_file: str,
    section: str,
    mode: str,
    modfqs: str = "1000.0",
    caldev: str = "2404.8",
    maxdev: str = "5000",
    headroom: str = "6",
    audiodev: str = "",
    flat: bool = False,
    wide: bool = False,
) -> Dict[str, Any]:

    if devcal_is_running():
        raise RuntimeError("devcal is already running.")

    prepare_devcal_input_pipe()

    cmd = build_devcal_command(
        config_file=config_file,
        section=section,
        mode=mode,
        modfqs=modfqs,
        caldev=caldev,
        maxdev=maxdev,
        headroom=headroom,
        audiodev=audiodev,
        flat=flat,
        wide=wide,
    )

    DEVCAL_LOG.write_text(
        "Starting devcal under PTY supervisor:\n"
        + " ".join(shlex.quote(part) for part in cmd)
        + "\n\n",
        encoding="utf-8",
    )

    supervisor = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-c",
            _devcal_supervisor_code(),
            str(DEVCAL_INPUT),
            str(DEVCAL_LOG),
            *cmd,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )

    DEVCAL_PID.write_text(str(supervisor.pid), encoding="utf-8")
    DEVCAL_MODE.write_text(mode, encoding="utf-8")
    set_devcal_tx_state("off")

    return {
        "command": " ".join(shlex.quote(part) for part in cmd),
        "returncode": 0,
        "stdout": f"devcal PTY supervisor started with PID {supervisor.pid}",
        "stderr": "",
    }


def toggle_devcal_tx() -> Dict[str, Any]:
    if not devcal_is_running():
        raise RuntimeError("devcal is not running.")

    mode = get_devcal_mode()

    if mode != "txcal":
        raise RuntimeError("TX toggle is only available during TX calibration.")

    if not DEVCAL_INPUT.exists():
        raise RuntimeError("devcal input pipe is not available.")

    fifo_mode = DEVCAL_INPUT.stat().st_mode

    if not stat.S_ISFIFO(fifo_mode):
        raise RuntimeError("devcal input path exists but is not a FIFO pipe.")

    with DEVCAL_INPUT.open("w", encoding="utf-8") as fh:
        fh.write("T\n")
        fh.flush()

    new_state = toggle_devcal_tx_state()

    return {
        "command": "send T to devcal PTY",
        "returncode": 0,
        "stdout": f"TX tone toggled {new_state.upper()}",
        "stderr": "",
    }


def stop_devcal_session() -> Dict[str, Any]:
    if not DEVCAL_PID.exists():
        DEVCAL_MODE.unlink(missing_ok=True)
        DEVCAL_TX_STATE.unlink(missing_ok=True)
        DEVCAL_INPUT.unlink(missing_ok=True)

        return {
            "command": "stop devcal",
            "returncode": 0,
            "stdout": "No devcal PID file found.",
            "stderr": "",
        }

    try:
        pid = int(DEVCAL_PID.read_text().strip())

        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        DEVCAL_PID.unlink(missing_ok=True)
        DEVCAL_MODE.unlink(missing_ok=True)
        DEVCAL_TX_STATE.unlink(missing_ok=True)
        DEVCAL_INPUT.unlink(missing_ok=True)

        return {
            "command": "stop devcal",
            "returncode": 0,
            "stdout": f"Stopped devcal PTY supervisor PID {pid}",
            "stderr": "",
        }

    except Exception as exc:
        return {
            "command": "stop devcal",
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }


def get_devcal_output(limit: int = 120) -> List[str]:
    if not DEVCAL_LOG.exists():
        return ["No devcal output yet."]

    try:
        lines = DEVCAL_LOG.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()

    except Exception as exc:
        return [f"Unable to read devcal output: {exc}"]

    return lines[-limit:]
