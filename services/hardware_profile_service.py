import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_DIR = BASE_DIR / "config" / "hardware_profiles"


def list_hardware_profiles():
    profiles = []

    if not PROFILE_DIR.exists():
        return profiles

    for path in sorted(PROFILE_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                profile = json.load(f)

            profiles.append({
                "profile_id": profile.get("profile_id", path.stem),
                "name": profile.get("name", path.stem),
                "ports": profile.get("ports", 1),
                "type": profile.get("type", "unknown")
            })

        except Exception:
            continue

    return profiles


def load_hardware_profile(profile_id):
    path = PROFILE_DIR / f"{profile_id}.json"

    if not path.exists():
        raise FileNotFoundError(f"Hardware profile not found: {profile_id}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_port_map(profile_id):
    profile = load_hardware_profile(profile_id)
    return profile.get("port_map", {})