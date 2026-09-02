#!/usr/bin/env python3

import re


def classify_macro_command(command):
    """
    Classify a stored SvxLink macro command without altering it.
    """

    command = str(command or "").strip()

    if command == "::910#":
        return {
            "type": "reflector_reset",
            "command": command,
        }

    if command == "::91#":
        return {
            "type": "reflector_recall",
            "command": command,
        }

    reflector_match = re.fullmatch(r"::91([1-9][0-9]*)#", command)

    if reflector_match:
        return {
            "type": "reflector_tg",
            "talkgroup": reflector_match.group(1),
            "command": command,
        }

    module_match = re.fullmatch(r"([^:]+):(.+)", command)

    if module_match and not command.startswith("::"):
        return {
            "type": "module",
            "module": module_match.group(1),
            "module_command": module_match.group(2),
            "command": command,
        }

    return {
        "type": "custom",
        "command": command,
    }

def build_macro_command(
    macro_type,
    talkgroup="",
    module="",
    module_command="",
    custom_command="",
):
    """
    Build a SvxLink macro command from dashboard fields.
    """

    macro_type = str(macro_type or "").strip()
    talkgroup = str(talkgroup or "").strip()
    module = str(module or "").strip()
    module_command = str(module_command or "").strip()
    custom_command = str(custom_command or "").strip()

    if macro_type == "reflector_reset":
        return "::910#"

    if macro_type == "reflector_recall":
        return "::91#"

    if macro_type == "reflector_tg":
        if not talkgroup.isdigit() or talkgroup == "0":
            raise ValueError("Reflector talkgroup must be a non-zero number.")

        return f"::91{talkgroup}#"

    if macro_type == "module":
        if not module or not module_command:
            raise ValueError(
                "Module macros require both a module name and command."
            )

        if not module_command.endswith("#"):
            module_command = f"{module_command}#"

        return f"{module}:{module_command}"

    if macro_type == "custom":
        if not custom_command:
            raise ValueError("Custom macro command cannot be empty.")

        return custom_command

    raise ValueError("Unknown macro type.")
