#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
from services.build_svxlink import build_svxlink_configuration
from services.build_svxlink import svxlink_status
from services.model_store import (
    load_node_model,
    save_node_model,
    reset_node_model,
)
import subprocess
import hw_platforms



# =========================================================
# Core paths
# =========================================================

APP_ROOT = Path("/opt/dashboard")
TEMPLATE_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"

# =========================================================
# SvxLink paths
# =========================================================

SVXLINK_CONF = Path("/etc/svxlink/svxlink.conf")

MODULE_DIR = Path("/etc/svxlink/svxlink.d")

LOGIC_DIR_SRC = Path("/usr/share/svxlink/events.d")

LOGIC_DIR_DST = Path("/usr/share/svxlink/events.d/local")

# =========================================================
# Flask app
# =========================================================

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)


# =========================================================
# Platform detection
# =========================================================

def detect_platform():
    """
    Detect supported hardware profile.

    Initial supported targets:
    - raspberry_pi
    - nanopi_neo

    Anything else is unsupported unless later proven compatible.
    """

    model_text = ""

    try:
        model_text = Path("/proc/device-tree/model").read_text(errors="ignore").lower()
    except FileNotFoundError:
        pass

    if "raspberry pi" in model_text:
        return {
            "id": "raspberry_pi",
            "name": "Raspberry Pi",
            "supported": True,
        }

    if "nanopi neo" in model_text or "friendlyarm nanopi" in model_text:
        return {
            "id": "nanopi_neo",
            "name": "NanoPi-Neo",
            "supported": True,
        }

    return {
        "id": "unknown",
        "name": hw_platforms.machine(),
        "supported": False,
    }


# =========================================================
# Node model defaults
# =========================================================

def default_node_model():
    """
    This is the authoritative in-memory model.
    svxlink.conf should eventually be generated from this.
    """

    return {
        "platform": detect_platform(),
        "node_type": None,          # simplex | repeater
        "callsign": None,
        "language": "en_US",

        "reflector": {
            "enabled": False,
            "name": None,
            "host": None,
            "port": None,
            "auth_key": None,
        },

        "ident": {
            "short": {
                "mode": None,       # none | cw | voice | both
                "interval": 15,
            },
            "long": {
                "mode": None,       # none | cw | voice | both
                "interval": 60,
            },
        },

        "roger": {
            "mode": "none",         # none | beep | morse_t | morse_k
        },

        "squelch": {
            "method": None,         # gpiod | ctcss
            "ctcss_freq": None,
            "ctcss_tx": False,
        },

        "modules": [
            "ModuleHelp",
            "ModuleParrot",
        ],
    }


# =========================================================
# Model persistence
# =========================================================

def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)



# =========================================================
# SvxLink service wrapper
# =========================================================

def svxlink_status():
    result = subprocess.run(
        ["systemctl", "is-active", "svxlink"],
        text=True,
        capture_output=True
    )

    return result.stdout.strip()


# =========================================================
# Routes
# =========================================================

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("setup"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    error = None
    model = load_node_model()

    if request.method == "POST":
        callsign = request.form.get("callsign", "").strip().upper()
        node_type = request.form.get("node_type")

        if not callsign:
            error = "Please enter a callsign."
        elif node_type not in ("simplex", "repeater"):
            error = "Please select Simplex or Repeater."
        else:
            model["callsign"] = callsign
            model["node_type"] = node_type

            save_node_model(model)
            return redirect(url_for("ident"))

    return render_template(
        "setup.html",
        error=error,
        model=model,
    )


@app.route("/ident", methods=["GET", "POST"])
def ident():
    error = None
    model = load_node_model()

    if request.method == "POST":
        short_mode = request.form.get("short_ident_mode")
        long_mode = request.form.get("long_ident_mode")

        try:
            short_interval = int(request.form.get("short_ident_interval", "15"))
            long_interval = int(request.form.get("long_ident_interval", "60"))
        except ValueError:
            error = "Identification intervals must be numbers."
        else:
            valid_modes = {"none", "cw", "voice", "both"}

            if short_mode not in valid_modes:
                error = "Please select a valid short identification mode."
            elif long_mode not in valid_modes:
                error = "Please select a valid long identification mode."
            else:
                model["ident"]["short"]["mode"] = short_mode
                model["ident"]["short"]["interval"] = short_interval
                model["ident"]["long"]["mode"] = long_mode
                model["ident"]["long"]["interval"] = long_interval

                save_node_model(model)
                return redirect(url_for("roger"))

    return render_template(
        "ident.html",
        error=error,
        model=model,
    )


@app.route("/roger", methods=["GET", "POST"])
def roger():
    error = None
    model = load_node_model()

    if request.method == "POST":
        roger_mode = request.form.get("roger_mode")

        valid_modes = {"none", "beep", "morse_t", "morse_k"}

        if roger_mode not in valid_modes:
            error = "Please select a valid roger tone option."
        else:
            # Repeater policy: roger tone is mandatory.
            if model["node_type"] == "repeater" and roger_mode == "none":
                error = "Repeater mode requires a roger tone."
            else:
                model["roger"]["mode"] = roger_mode
                save_node_model(model)
                return redirect(url_for("connect"))

    return render_template(
        "roger.html",
        error=error,
        model=model,
    )


@app.route("/connect", methods=["GET", "POST"])
def connect():
    error = None
    model = load_node_model()

    reflectors = {
        "north_america": {
            "name": "North America Reflector",
            "host": "north.america.svxlink.net",
            "port": 35300,
            "url": "https://north.america.svxlink.net",
        },
        "ukwide": {
            "name": "UKWide Reflector",
            "host": "uk.wide.svxlink.uk",
            "port": 35300,
            "url": "https://ukwide.svxlink.net",
        },
        "australia_nz": {
            "name": "Australia / New Zealand Reflector",
            "host": "australia.svxlink.net",
            "port": 35300,
            "url": "https://au.svxlink.net",
        },
        "yorkshire": {
            "name": "YorkshireNet Reflector",
            "host": "yorkshire.svxlink.uk",
            "port": 5310,
            "url": "https://svxlink.qsos.uk/",
        },
    }

    if request.method == "POST":
        connect_answer = request.form.get("connect")
        reflector_id = request.form.get("reflector")
        password = request.form.get("password", "").strip()

        if connect_answer == "no":
            model["reflector"]["enabled"] = False
            save_node_model(model)
            return redirect(url_for("done"))

        if reflector_id not in reflectors:
            error = "Please select a reflector."
        elif not password:
            error = "Please enter the reflector subscription password."
        elif len(password) != 16:
            error = "Password must be exactly 16 characters long."
        else:
            selected = reflectors[reflector_id]

            model["reflector"] = {
                "enabled": True,
                "name": selected["name"],
                "host": selected["host"],
                "port": selected["port"],
                "auth_key": password,
            }

            save_node_model(model)
            return redirect(url_for("done"))

    return render_template(
        "connect.html",
        error=error,
        model=model,
        reflectors=reflectors,
    )

@app.route("/done", methods=["GET"])
def done():
    model = load_node_model()

    return render_template(
        "done.html",
        model=model,
        svxlink_status=svxlink_status(),
        build_result=None,
    )

@app.route("/launch", methods=["POST"])
def launch():
    model = load_node_model()

    result = build_svxlink_configuration(
        model,
        restart=True,
    )

    return render_template(
        "done.html",
        model=model,
        svxlink_status=result.get("service_status"),
        build_result=result,
        error=None if result.get("success") else "Build or launch failed.",
    )

# =========================================================
# Wizard routes
# =========================================================

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("start"))


@app.route("/start", methods=["GET", "POST"])
def start():
    model = load_node_model()

    if request.method == "POST":
        return redirect(url_for("platform_page"))

    return render_template("start.html", model=model)


@app.route("/platform", methods=["GET", "POST"])
def platform_page():
    model = load_node_model()

    if request.method == "POST":
        # Platform is normally detected, not user-selected.
        save_node_model(model)
        return redirect(url_for("node_page"))

    return render_template("platform.html", model=model)


@app.route("/node", methods=["GET", "POST"])
def node_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        node_type = request.form.get("node_type")
        callsign = request.form.get("callsign", "").strip().upper()

        if node_type not in ("simplex", "repeater"):
            error = "Please select Simplex or Repeater."
        elif not callsign:
            error = "Please enter a callsign."
        else:
            model["node"]["type"] = node_type
            model["node"]["callsign"] = callsign
            save_node_model(model)
            return redirect(url_for("interface_page"))

    return render_template("node.html", model=model, error=error)


@app.route("/interface", methods=["GET", "POST"])
def interface_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        interface_mode = request.form.get("interface_mode")

        try:
            from models.node_model import set_interface_mode
            set_interface_mode(model, interface_mode)
            save_node_model(model)
            return redirect(url_for("squelch_page"))
        except ValueError as exc:
            error = str(exc)

    return render_template("interface.html", model=model, error=error)


@app.route("/squelch", methods=["GET", "POST"])
def squelch_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        squelch_method = request.form.get("squelch_method")

        model["squelch"]["method"] = squelch_method

        # CTCSS details will be expanded later.
        ctcss_freq = request.form.get("ctcss_freq")
        if ctcss_freq:
            model["squelch"]["ctcss_freq"] = ctcss_freq

        model["squelch"]["ctcss_tx"] = (
            request.form.get("ctcss_tx") == "yes"
        )

        save_node_model(model)
        return redirect(url_for("ident_page"))

    return render_template("squelch.html", model=model, error=error)


@app.route("/ident", methods=["GET", "POST"])
def ident_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        try:
            model["ident"]["short"]["mode"] = request.form.get("short_ident_mode")
            model["ident"]["short"]["interval"] = int(request.form.get("short_ident_interval", "15"))

            model["ident"]["long"]["mode"] = request.form.get("long_ident_mode")
            model["ident"]["long"]["interval"] = int(request.form.get("long_ident_interval", "60"))

            save_node_model(model)
            return redirect(url_for("modules_page"))

        except ValueError:
            error = "Identification intervals must be numeric."

    return render_template("ident.html", model=model, error=error)


@app.route("/modules", methods=["GET", "POST"])
def modules_page():
    model = load_node_model()

    if request.method == "POST":
        modules = [
            "ModuleHelp",
            "ModuleParrot",
        ]

        if request.form.get("module_echolink") == "yes":
            modules.append("ModuleEchoLink")

        if request.form.get("module_metar") == "yes":
            modules.append("ModuleMetarInfo")

        model["modules"]["enabled"] = modules
        save_node_model(model)

        return redirect(url_for("reflector_page"))

    return render_template("modules.html", model=model)


@app.route("/reflector", methods=["GET", "POST"])
def reflector_page():
    model = load_node_model()
    error = None

    reflectors = {
        "north_america": {
            "name": "North America Reflector",
            "host": "north.america.svxlink.net",
            "port": 35300,
            "url": "https://north.america.svxlink.net",
            "monitor_tgs": 3100,
        },
        "ukwide": {
            "name": "UKWide Reflector",
            "host": "uk.wide.svxlink.uk",
            "port": 35300,
            "url": "https://ukwide.svxlink.net",
            "monitor_tgs": 235,
        },
        "australia_nz": {
            "name": "Australia / New Zealand Reflector",
            "host": "australia.svxlink.net",
            "port": 35300,
            "url": "https://au.svxlink.net",
            "monitor_tgs": 505,
        },
        "yorkshire": {
            "name": "YorkshireNet Reflector",
            "host": "yorkshire.svxlink.uk",
            "port": 5310,
            "url": "https://svxlink.qsos.uk/",
            "monitor_tgs": 235,
        },
    }

    if request.method == "POST":
        connect = request.form.get("connect")

        if connect == "no":
            model["reflector"]["enabled"] = False
            model["reflector"]["name"] = None
            model["reflector"]["host"] = None
            model["reflector"]["port"] = None
            model["reflector"]["auth_key"] = None

            save_node_model(model)
            return redirect(url_for("review_page"))

        reflector_id = request.form.get("reflector")
        password = request.form.get("password", "").strip()

        if reflector_id not in reflectors:
            error = "Please select a reflector."
        elif len(password) != 16:
            error = "Reflector password must be exactly 16 characters."
        else:
            selected = reflectors[reflector_id]

            model["reflector"]["enabled"] = True
            model["reflector"]["name"] = selected["name"]
            model["reflector"]["host"] = selected["host"]
            model["reflector"]["port"] = selected["port"]
            model["reflector"]["auth_key"] = password

            save_node_model(model)
            return redirect(url_for("review_page"))

    return render_template(
        "reflector.html",
        model=model,
        reflectors=reflectors,
        error=error,
    )


@app.route("/review", methods=["GET", "POST"])
def review_page():
    model = load_node_model()

    if request.method == "POST":
        return redirect(url_for("build_page"))

    return render_template("review.html", model=model)


@app.route("/build", methods=["GET", "POST"])
def build_page():
    model = load_node_model()
    result = None

    if request.method == "POST":
        result = build_svxlink_configuration(
            model,
            restart=False,
        )

        if result.get("success"):
            return redirect(url_for("done"))

    return render_template(
        "build.html",
        model=model,
        build_result=result,
    )


@app.route("/done", methods=["GET"])
def done():
    model = load_node_model()

    return render_template(
        "done.html",
        model=model,
        svxlink_status=svxlink_status(),
    )


@app.route("/launch", methods=["POST"])
def launch():
    model = load_node_model()

    result = build_svxlink_configuration(
        model,
        restart=True,
    )

    return render_template(
        "done.html",
        model=model,
        svxlink_status=result.get("service_status"),
        build_result=result,
        error=None if result.get("success") else "Build or launch failed.",
    )
    
if __name__ == "__main__":
    ensure_dirs()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )