#!/usr/bin/env python3

"""
Platform detection and profile selection for SvxLink-Dash-V3.
"""

from pathlib import Path
import hw_platforms as py_platform

from .nanopi import PROFILE as NANOPI_PROFILE
from .raspberry import PROFILE as RASPBERRY_PROFILE


SUPPORTED_PROFILES = {
    "nanopi_neo": NANOPI_PROFILE,
    "raspberry_pi": RASPBERRY_PROFILE,
}


def detect_platform_id():
    """
    Detect supported platform from /proc/device-tree/model.

    Returns:
        str: raspberry_pi, nanopi_neo, or unknown
    """

    model_text = ""

    try:
        model_text = Path("/proc/device-tree/model").read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()
    except FileNotFoundError:
        pass

    if "raspberry pi" in model_text:
        return "raspberry_pi"

    if "nanopi neo" in model_text or "friendlyarm nanopi" in model_text:
        return "nanopi_neo"

    return "unknown"


def get_platform_profile(platform_id=None):
    """
    Return platform profile.

    If platform_id is None, auto-detect.
    """

    if platform_id is None:
        platform_id = detect_platform_id()

    if platform_id in SUPPORTED_PROFILES:
        return SUPPORTED_PROFILES[platform_id]

    return {
        "id": "unknown",
        "name": py_platform.machine(),
        "supported": False,
        "allowed_node_types": [],
        "allowed_interface_modes": [],
        "allowed_squelch_modes": [],
        "default_interface_mode": None,
        "gpio": {},
        "audio": {},
        "notes": [
            "Unsupported or unknown platform.",
        ],
    }


def validate_platform_model(model):
    """
    Validate model against detected platform capability.

    Returns:
        list[str]
    """

    errors = []

    platform_id = model.get("platform", {}).get("id")
    profile = get_platform_profile(platform_id)

    if not profile.get("supported"):
        errors.append("Unsupported platform.")
        return errors

    node_type = model.get("node", {}).get("type")
    interface_mode = model.get("interface", {}).get("mode")
    squelch_method = model.get("squelch", {}).get("method")

    if node_type and node_type not in profile["allowed_node_types"]:
        errors.append(f"{profile['name']} does not support node type: {node_type}")

    if interface_mode and interface_mode not in profile["allowed_interface_modes"]:
        errors.append(f"{profile['name']} does not support interface mode: {interface_mode}")

    if squelch_method and squelch_method not in profile["allowed_squelch_modes"]:
        errors.append(f"{profile['name']} does not support squelch mode: {squelch_method}")

    return errors