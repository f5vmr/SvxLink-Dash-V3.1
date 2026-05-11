#!/usr/bin/env python3

"""
Primary build orchestration service for SvxLink-Dash-V3.

This module coordinates:
- model validation
- platform validation
- configuration rendering
- backup creation
- file deployment
- optional service restart

This is the authoritative build pipeline.
"""

from pathlib import Path
import subprocess

from models.node_model import validate_model

from hw_platforms import (
    validate_platform_model,
)

from renderers.svxlink_renderer import (
    render_svxlink_config,
    render_echolink_module,
    render_metar_module,
)

from services.svxlink_service import (
    backup_active_config,
    write_text_file,
    deploy_required_logic_files,
    restart_svxlink,
    svxlink_status,
)

from services.svxlink_service import (
    SVXLINK_CONF,
    MODULE_DIR,
)


# =========================================================
# Build result helper
# =========================================================

def build_result():
    """
    Standard structured build result.
    """

    return {
        "success": False,

        "validation_errors": [],
        "platform_errors": [],
        "deployment_errors": [],

        "rendered_files": [],
        "backups": [],
        "logic_files": [],

        "service_restarted": False,
        "service_status": "unknown",
    }


# =========================================================
# Validation
# =========================================================

def validate_build(model):
    """
    Validate complete build readiness.

    Returns:
        dict
    """

    result = build_result()

    validation_errors = validate_model(model)
    platform_errors = validate_platform_model(model)

    result["validation_errors"] = validation_errors
    result["platform_errors"] = platform_errors

    return result


# =========================================================
# Render phase
# =========================================================

def render_all(model):
    """
    Render all required configuration outputs.

    Returns:
        dict
    """

    rendered = {}

    # =====================================================
    # Main SvxLink configuration
    # =====================================================

    rendered["svxlink.conf"] = render_svxlink_config(model)

    # =====================================================
    # Optional module configurations
    # =====================================================

    echolink_conf = render_echolink_module(model)

    if echolink_conf:
        rendered["ModuleEchoLink.conf"] = echolink_conf

    metar_conf = render_metar_module(model)

    if metar_conf:
        rendered["ModuleMetarInfo.conf"] = metar_conf

    return rendered

# =========================================================
# Deployment phase
# =========================================================

def deploy_rendered_files(rendered_files):
    """
    Deploy rendered configuration files.

    Returns:
        list[str]
    """

    deployed = []

    # =====================================================
    # Main svxlink.conf
    # =====================================================

    if "svxlink.conf" in rendered_files:

        write_text_file(
            SVXLINK_CONF,
            rendered_files["svxlink.conf"]
        )

        deployed.append(str(SVXLINK_CONF))

    # =====================================================
    # Optional module configuration files
    # =====================================================

    for filename in (
        "ModuleEchoLink.conf",
        "ModuleMetarInfo.conf",
    ):

        if filename not in rendered_files:
            continue

        target = MODULE_DIR / filename

        write_text_file(
            target,
            rendered_files[filename]
        )

        deployed.append(str(target))

    return deployed

# =========================================================
# Full build pipeline
# =========================================================

def build_svxlink_configuration(
    model,
    restart=False,
):
    """
    Execute full configuration build pipeline.

    Steps:
        1. Validate model
        2. Validate platform
        3. Render config
        4. Backup active config
        5. Deploy config
        6. Deploy logic files
        7. Restart service optionally

    Returns:
        dict
    """

    result = build_result()

    # =====================================================
    # Validation
    # =====================================================

    validation = validate_build(model)

    result["validation_errors"] = validation["validation_errors"]
    result["platform_errors"] = validation["platform_errors"]

    if (
        result["validation_errors"]
        or
        result["platform_errors"]
    ):
        result["service_status"] = svxlink_status()
        return result

    # =====================================================
    # Render
    # =====================================================

    try:
        rendered = render_all(model)

    except Exception as exc:

        result["deployment_errors"].append(
            f"Render failed: {exc}"
        )

        result["service_status"] = svxlink_status()
        return result

    # =====================================================
    # Backup
    # =====================================================

    try:
        backups = backup_active_config()
        result["backups"] = [str(x) for x in backups]

    except Exception as exc:

        result["deployment_errors"].append(
            f"Backup failed: {exc}"
        )

        result["service_status"] = svxlink_status()
        return result

    # =====================================================
    # Deploy config
    # =====================================================

    try:
        deployed = deploy_rendered_files(rendered)

        result["rendered_files"] = deployed

    except Exception as exc:

        result["deployment_errors"].append(
            f"Configuration deployment failed: {exc}"
        )

        result["service_status"] = svxlink_status()
        return result

    # =====================================================
    # Deploy logic overrides
    # =====================================================

    try:
        logic_files = deploy_required_logic_files()

        result["logic_files"] = [
            str(x) for x in logic_files
        ]

    except Exception as exc:

        result["deployment_errors"].append(
            f"Logic deployment failed: {exc}"
        )

        result["service_status"] = svxlink_status()
        return result

    # =====================================================
    # Restart service
    # =====================================================

    if restart:

        try:
            restart_svxlink()
            result["service_restarted"] = True

        except Exception as exc:

            result["deployment_errors"].append(
                f"SvxLink restart failed: {exc}"
            )

    # =====================================================
    # Final status
    # =====================================================

    result["service_status"] = svxlink_status()

    if not result["deployment_errors"]:
        result["success"] = True

    return result