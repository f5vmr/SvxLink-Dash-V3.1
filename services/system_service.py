#!/usr/bin/env python3

"""
System maintenance helpers for SvxLink-Dash-V3.
"""

import subprocess


def restart_services():
    """
    Restart SvxLink and dashboard services.
    """

    subprocess.Popen(
        [
            "sudo",
            "/bin/sh",
            "-c",
            "sleep 2; /usr/bin/systemctl restart svxlink svxlink-dash",
        ]
    )


def reboot_device():
    """
    Reboot the device.
    """

    subprocess.Popen(
        [
            "sudo",
            "/usr/sbin/shutdown",
            "-r",
            "now",
        ]
    )


def shutdown_device():
    """
    Shut down the device.
    """

    subprocess.Popen(
        [
            "sudo",
            "/usr/sbin/shutdown",
            "-h",
            "now",
        ]
    )