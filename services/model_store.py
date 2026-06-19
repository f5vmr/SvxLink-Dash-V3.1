#!/usr/bin/env python3

"""
Node model persistence for SvxLink Dashboard V3.1.
"""

import json
from pathlib import Path

from models.node_model import new_node_model
from hw_platforms import get_platform_profile


APP_ROOT = Path("/opt/dashboard")
CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"
CTCSS_TONES = [
    ("", "None / disabled"),
    ("67.0", "67.0 Hz"),
    ("69.3", "69.3 Hz"),
    ("71.9", "71.9 Hz"),
    ("74.4", "74.4 Hz"),
    ("77.0", "77.0 Hz"),
    ("79.7", "79.7 Hz"),
    ("82.5", "82.5 Hz"),
    ("85.4", "85.4 Hz"),
    ("88.5", "88.5 Hz"),
    ("91.5", "91.5 Hz"),
    ("94.8", "94.8 Hz"),
    ("97.4", "97.4 Hz"),
    ("100.0", "100.0 Hz"),
    ("103.5", "103.5 Hz"),
    ("107.2", "107.2 Hz"),
    ("110.9", "110.9 Hz"),
    ("114.8", "114.8 Hz"),
    ("118.8", "118.8 Hz"),
    ("123.0", "123.0 Hz"),
    ("127.3", "127.3 Hz"),
    ("131.8", "131.8 Hz"),
    ("136.5", "136.5 Hz"),
    ("141.3", "141.3 Hz"),
    ("146.2", "146.2 Hz"),
    ("151.4", "151.4 Hz"),
    ("156.7", "156.7 Hz"),
    ("159.8", "159.8 Hz"),
    ("162.2", "162.2 Hz"),
    ("165.5", "165.5 Hz"),
    ("167.9", "167.9 Hz"),
    ("171.3", "171.3 Hz"),
    ("173.8", "173.8 Hz"),
    ("177.3", "177.3 Hz"),
    ("179.9", "179.9 Hz"),
    ("183.5", "183.5 Hz"),
    ("186.2", "186.2 Hz"),
    ("189.9", "189.9 Hz"),
    ("192.8", "192.8 Hz"),
    ("196.6", "196.6 Hz"),
    ("199.5", "199.5 Hz"),
    ("203.5", "203.5 Hz"),
    ("206.5", "206.5 Hz"),
    ("210.7", "210.7 Hz"),
    ("218.1", "218.1 Hz"),
    ("225.7", "225.7 Hz"),
    ("229.1", "229.1 Hz"),
    ("233.6", "233.6 Hz"),
    ("241.8", "241.8 Hz"),
    ("250.3", "250.3 Hz"),
    ("254.1", "254.1 Hz"),
]


def normalise_ctcss_tone(value):
    value = str(value or "").strip()

    valid_values = {
        tone_value
        for tone_value, _label in CTCSS_TONES
    }

    if value in valid_values:
        return value

    return ""

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

    if not MODEL_FILE.exists() or MODEL_FILE.stat().st_size == 0:
        model = create_default_model()
        save_node_model(model)
        return model

    try:
        return json.loads(
            MODEL_FILE.read_text(encoding="utf-8")
        )

    except json.JSONDecodeError:
        corrupt_file = MODEL_FILE.with_suffix(".json.corrupt")
        MODEL_FILE.rename(corrupt_file)

        model = create_default_model()
        save_node_model(model)
        return model

def reset_node_model():
    model = create_default_model()
    save_node_model(model)
    return model