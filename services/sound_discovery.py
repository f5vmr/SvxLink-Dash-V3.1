#!/usr/bin/env python3

import re
import subprocess
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class AlsaControl:
    numid: int
    iface: str
    name: str
    control_type: Optional[str] = None
    access: Optional[str] = None
    values_count: Optional[int] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    step: Optional[int] = None
    current_values: Optional[List[str]] = None
    db_min: Optional[str] = None
    db_max: Optional[str] = None
    raw: str = ""
    role: str = "unknown"
    confidence: str = "low"
    safe_action: str = "none"


@dataclass
class AlsaCard:
    index: int
    name: str
    description: str
    has_playback: bool = False
    has_capture: bool = False
    controls: Optional[List[AlsaControl]] = None
    likely_role: str = "unknown"
    confidence: str = "low"


def run_cmd(cmd: List[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0 and result.stderr:
            return result.stderr.strip()
        return result.stdout.strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def parse_proc_asound_cards() -> List[AlsaCard]:
    cards: List[AlsaCard] = []

    try:
        with open("/proc/asound/cards", "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return cards

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        match = re.match(r"\s*(\d+)\s+\[([^\]]+)\]:\s+(.+)", line)

        if not match:
            i += 1
            continue

        index = int(match.group(1))
        name = match.group(2).strip()
        first_desc = match.group(3).strip()
        second_desc = ""

        if i + 1 < len(lines):
            second_desc = lines[i + 1].strip()

        cards.append(
            AlsaCard(
                index=index,
                name=name,
                description=f"{first_desc} {second_desc}".strip(),
            )
        )

        i += 2

    return cards


def card_has_device(card_index: int, command: str) -> bool:
    output = run_cmd([command, "-l"])
    return bool(re.search(rf"\bcard\s+{card_index}\b", output, re.IGNORECASE))


def split_amixer_contents_blocks(contents: str) -> List[str]:
    blocks: List[str] = []
    current: List[str] = []

    for line in contents.splitlines():
        if line.startswith("numid="):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)

    if current:
        blocks.append("\n".join(current))

    return blocks


def parse_values_list(value_text: str) -> List[str]:
    return [part.strip() for part in value_text.split(",") if part.strip()]


def parse_control_block(block: str) -> Optional[AlsaControl]:
    lines = block.splitlines()
    header = lines[0] if lines else ""

    header_match = re.match(
        r"numid=(\d+),iface=([^,]+),name='([^']+)'",
        header,
    )

    if not header_match:
        return None

    control = AlsaControl(
        numid=int(header_match.group(1)),
        iface=header_match.group(2).strip(),
        name=header_match.group(3).strip(),
        raw=block,
    )

    for line in lines[1:]:
        stripped = line.strip()

        meta_match = re.match(
            r";\s*type=([^,]+),access=([^,]+),values=(\d+)(?:,min=(-?\d+),max=(-?\d+),step=(-?\d+))?",
            stripped,
        )
        if meta_match:
            control.control_type = meta_match.group(1)
            control.access = meta_match.group(2)
            control.values_count = int(meta_match.group(3))

            if meta_match.group(4) is not None:
                control.min_value = int(meta_match.group(4))
                control.max_value = int(meta_match.group(5))
                control.step = int(meta_match.group(6))
            continue

        values_match = re.match(r":\s*values=(.+)", stripped)
        if values_match:
            control.current_values = parse_values_list(values_match.group(1))
            continue

        db_match = re.match(
            r"\|\s*dBminmax-min=([^,]+),max=(.+)",
            stripped,
        )
        if db_match:
            control.db_min = db_match.group(1).strip()
            control.db_max = db_match.group(2).strip()
            continue

    classify_control(control)
    return control


def classify_control(control: AlsaControl) -> None:
    name = control.name.lower()

    is_switch = control.control_type == "BOOLEAN"
    is_volume = control.control_type == "INTEGER" and control.min_value is not None and control.max_value is not None

    if "auto gain" in name or name == "agc" or "agc" in name:
        control.role = "agc"
        control.confidence = "high"
        control.safe_action = "force_off"
        return

    if "mic playback" in name:
        if is_switch:
            control.role = "mic_playback_switch"
            control.safe_action = "force_off"
        elif is_volume:
            control.role = "mic_playback_volume"
            control.safe_action = "force_min"
        else:
            control.role = "mic_playback"
            control.safe_action = "none"

        control.confidence = "high"
        return

    if "mic capture" in name:
        if is_switch:
            control.role = "mic_capture_switch"
            control.safe_action = "force_on"
        elif is_volume:
            control.role = "mic_capture_volume"
            control.safe_action = "slider"
        else:
            control.role = "mic_capture"
            control.safe_action = "none"

        control.confidence = "high"
        return

    if "capture" in name and "channel map" not in name:
        if is_switch:
            control.role = "capture_switch"
            control.safe_action = "force_on"
        elif is_volume:
            control.role = "capture_volume"
            control.safe_action = "slider"
        else:
            control.role = "capture"
            control.safe_action = "none"

        control.confidence = "medium"
        return

    if any(word in name for word in ["speaker playback", "headphone playback", "loudspeaker playback", "pcm playback"]):
        if is_switch:
            control.role = "output_switch"
            control.safe_action = "force_on"
        elif is_volume:
            control.role = "output_volume"
            control.safe_action = "slider"
        else:
            control.role = "output"
            control.safe_action = "none"

        control.confidence = "high"
        return

    if "playback channel map" in name:
        control.role = "playback_channel_map"
        control.confidence = "high"
        control.safe_action = "none"
        return

    if "capture channel map" in name:
        control.role = "capture_channel_map"
        control.confidence = "high"
        control.safe_action = "none"
        return


def parse_amixer_contents(card_index: int) -> List[AlsaControl]:
    contents = run_cmd(["amixer", "-c", str(card_index), "contents"])
    controls: List[AlsaControl] = []

    for block in split_amixer_contents_blocks(contents):
        parsed = parse_control_block(block)
        if parsed:
            controls.append(parsed)

    return controls


def classify_card(card: AlsaCard) -> None:
    desc = f"{card.name} {card.description}".lower()

    if "loopback" in desc:
        card.likely_role = "virtual_loopback"
        card.confidence = "high"
        return

    if "hdmi" in desc:
        card.likely_role = "hdmi_or_output_only"
        card.confidence = "high"
        return

    roles = {control.role for control in card.controls or []}

    has_output = any(role in roles for role in ["output_volume", "output_switch"])
    has_input = any(role in roles for role in ["mic_capture_volume", "capture_volume", "mic_capture_switch", "capture_switch"])

    if card.has_playback and card.has_capture and has_output and has_input:
        card.likely_role = "radio_audio_candidate"
        card.confidence = "high"
    elif card.has_playback and card.has_capture:
        card.likely_role = "radio_audio_candidate"
        card.confidence = "medium"
    elif card.has_playback:
        card.likely_role = "playback_only"
        card.confidence = "medium"
    elif card.has_capture:
        card.likely_role = "capture_only"
        card.confidence = "medium"
    else:
        card.likely_role = "unknown"
        card.confidence = "low"


def discover_sound_cards() -> List[Dict[str, Any]]:
    cards = parse_proc_asound_cards()

    for card in cards:
        card.has_playback = card_has_device(card.index, "aplay")
        card.has_capture = card_has_device(card.index, "arecord")
        card.controls = parse_amixer_contents(card.index)
        classify_card(card)

    return [
        {
            **asdict(card),
            "controls": [asdict(control) for control in card.controls or []],
        }
        for card in cards
    ]

def percent_to_raw(control: AlsaControl, percent: int) -> Optional[int]:
    if control.min_value is None or control.max_value is None:
        return None

    percent = max(0, min(100, percent))
    span = control.max_value - control.min_value
    return round(control.min_value + (span * percent / 100))


def cset_control(card_index: int, control: AlsaControl, value: str) -> Dict[str, Any]:
    output = run_cmd([
        "amixer",
        "-c",
        str(card_index),
        "cset",
        f"numid={control.numid}",
        value,
    ])

    return {
        "numid": control.numid,
        "name": control.name,
        "role": control.role,
        "value": value,
        "output": output,
    }


def apply_safe_baseline(card_index: int) -> Dict[str, Any]:
    controls = parse_amixer_contents(card_index)
    actions: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for control in controls:
        action = control.safe_action

        if action == "force_off":
            actions.append(cset_control(card_index, control, "off"))

        elif action == "force_on":
            actions.append(cset_control(card_index, control, "on"))

        elif action == "force_min":
            if control.min_value is not None:
                actions.append(cset_control(card_index, control, str(control.min_value)))
            else:
                skipped.append({
                    "numid": control.numid,
                    "name": control.name,
                    "reason": "no minimum value available",
                })

        elif action == "slider":
            if control.role == "output_volume":
                raw = percent_to_raw(control, 77)
            elif control.role in ["mic_capture_volume", "capture_volume"]:
                raw = percent_to_raw(control, 41)
            else:
                raw = None

            if raw is not None:
                value = ",".join([str(raw)] * (control.values_count or 1))
                actions.append(cset_control(card_index, control, value))
            else:
                skipped.append({
                    "numid": control.numid,
                    "name": control.name,
                    "reason": "slider role but no baseline value",
                })

        else:
            skipped.append({
                "numid": control.numid,
                "name": control.name,
                "role": control.role,
                "reason": "no safe automatic action",
            })

    store_output = run_cmd(["alsactl", "store"])

    return {
        "card_index": card_index,
        "actions": actions,
        "skipped": skipped,
        "alsactl_store": store_output,
    }
def set_slider_control(card_index: int, numid: int, raw_value: int) -> Dict[str, Any]:
    controls = parse_amixer_contents(card_index)

    selected = None
    for control in controls:
        if control.numid == numid:
            selected = control
            break

    if selected is None:
        raise ValueError(f"Control numid={numid} was not found on card {card_index}")

    if selected.safe_action != "slider":
        raise ValueError(f"Control '{selected.name}' is not approved for slider adjustment")

    if selected.min_value is None or selected.max_value is None:
        raise ValueError(f"Control '{selected.name}' has no usable numeric range")

    raw_value = max(selected.min_value, min(selected.max_value, raw_value))

    value = ",".join([str(raw_value)] * (selected.values_count or 1))

    result = cset_control(card_index, selected, value)

    store_output = run_cmd(["alsactl", "store"])

    return {
        "card_index": card_index,
        "numid": selected.numid,
        "name": selected.name,
        "role": selected.role,
        "value": value,
        "result": result,
        "alsactl_store": store_output,
    }
if __name__ == "__main__":
    import json

    print(json.dumps(discover_sound_cards(), indent=2))