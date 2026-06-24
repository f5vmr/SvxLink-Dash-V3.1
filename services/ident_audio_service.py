from pathlib import Path
import re
import subprocess
import tempfile
from werkzeug.datastructures import FileStorage


IDENT_SOUND_DIR = Path("/var/lib/svxlink-dash/sounds/idents")


def safe_ident_name(name):
    """
    Keep generated ident audio filenames predictable and safe.
    """

    name = str(name or "").lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = name.strip("_")

    return name or "ident"


def validate_ident_wav(path):
    """
    Confirm the converted WAV is suitable for SvxLink ident playback.
    """

    path = Path(path)

    result = subprocess.run(
        ["soxi", str(path)],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return {
            "ok": False,
            "error": result.stderr.strip() or result.stdout.strip(),
            "details": result.stdout.strip(),
        }

    output = result.stdout

    checks = {
        "Channels       : 1": "File must be mono.",
        "Sample Rate    : 16000": "File must be 16000 Hz.",
        "Precision      : 16-bit": "File must be 16-bit PCM.",
    }

    for marker, message in checks.items():
        if marker not in output:
            return {
                "ok": False,
                "error": message,
                "details": output,
            }

    if path.stat().st_size <= 44:
        return {
            "ok": False,
            "error": "Converted WAV file is empty or invalid.",
            "details": output,
        }

    return {
        "ok": True,
        "error": "",
        "details": output,
    }


def save_ident_upload(upload: FileStorage, output_name: str):
    """
    Save and convert uploaded audio to SvxLink-safe WAV.

    Target:
        WAV, mono, 16-bit PCM, 16000 Hz
    """

    if not upload or not upload.filename:
        return None

    IDENT_SOUND_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_name = safe_ident_name(output_name)
    output_path = IDENT_SOUND_DIR / f"{output_name}.wav"

    suffix = Path(upload.filename).suffix or ".wav"

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    ) as tmp:
        upload.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        subprocess.run(
            [
                "sox",
                str(tmp_path),
                "-r",
                "16000",
                "-b",
                "16",
                "-c",
                "1",
                str(output_path),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        validation = validate_ident_wav(output_path)

        if not validation["ok"]:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                "Converted ident audio is not SvxLink compatible: "
                + validation["error"]
            )

        output_path.chmod(0o664)

    finally:
        tmp_path.unlink(missing_ok=True)

    return str(output_path)