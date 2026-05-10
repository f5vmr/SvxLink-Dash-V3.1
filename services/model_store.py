#!/usr/bin/env python3

"""
Node model persistence for SvxLink-Dash-V3.
"""

import json
from pathlib import Path

from models.node_model import new_node_model
from platform import get_platform_profile


APP_ROOT = Path("/opt/dashboard")
CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def create_default_model():
    platform = get_platform_profile()
    return new_node_model(platform=platform)


def save_node_model(model):
    ensure_config_dir()

    MODEL_FILE.write_text(
        json.dumps(model, indent=4),
        encoding="utf-8",
    )


def load_node_model():
    ensure_config_dir()

    if not MODEL_FILE.exists():
        model = create_default_model()
        save_node_model(model)
        return model

    return json.loads(
        MODEL_FILE.read_text(encoding="utf-8")
    )


def reset_node_model():
    model = create_default_model()
    save_node_model(model)
    return model