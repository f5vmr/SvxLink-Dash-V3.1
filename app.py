#!/usr/bin/env python3

from pyexpat import model

from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from services.build_svxlink import build_svxlink_configuration
from services.build_svxlink import svxlink_status
from services.model_store import (
    load_node_model,
    save_node_model,
)
from services.talkgroup_service import load_talkgroups, save_talkgroups
from services.dtmf_service import send_dtmf
from services.status_service import get_runtime_status
from services.activity_service import get_reflector_activity
from services.hardware_service import get_system_info
from services.svxlink_service import restart_svxlink
from renderers.svxlink_renderer import (
    render_echolink_module,
    render_metar_module,
)

from services.svxlink_service import (
    MODULE_DIR,
    write_text_file,
    restart_svxlink,
)
import subprocess
import hw_platforms
from data.metar_airports import METAR_REGIONS
from data.timezones import TIMEZONES



# =========================================================
# Core paths
# =========================================================

APP_ROOT = Path("/opt/dashboard")
TEMPLATE_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"
# =========================================================
# Supported CTCSS frequencies
# =========================================================
CTCSS_FREQUENCIES = [
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7,
    82.5, 85.4, 88.5, 91.5, 94.8, 97.4,
    100.0, 103.5, 107.2, 110.9, 114.8, 118.8,
    123.0, 127.3, 131.8, 136.5, 141.3, 146.2,
    151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2,
    189.9, 192.8, 196.6, 199.5, 203.5, 206.5,
    210.7, 218.1, 225.7, 229.1, 233.6, 241.8,
    250.3, 254.1,
]

# =========================================================
# SvxLink paths
# =========================================================

SVXLINK_CONF = Path("/etc/svxlink/svxlink.conf")

MODULE_DIR = Path("/etc/svxlink/svxlink.d")

EVENT_SOURCE_DIR = Path("/usr/share/svxlink/events.d")

EVENT_DEST_DIR = Path("/usr/share/svxlink/events.d/local")
EVENT_FILES = ['Logic.tcl', 'RepeaterLogicType.tcl']
# =========================================================
# Flask app
# =========================================================

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)
app.secret_key = "change-this-dashboard-secret"

from datetime import timedelta
app.permanent_session_lifetime = timedelta(minutes=15)

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
        return redirect(url_for("environment_page"))

    return render_template("platform.html", model=model)

@app.route("/environment", methods=["GET", "POST"])
def environment_page():
    model = load_node_model()
    error = None

    if "environment" not in model:
        model["environment"] = {}

    if request.method == "POST":

        environment = request.form.get("environment", "").strip()

        if not environment:
            error = "Please select an operating environment."

        else:

            if environment == "north_america":
                language = "en_US"
                metar_region = "north_america"

            elif environment == "australia_nz":
                language = "en_GB"
                metar_region = "australia"

            else:
                environment = "british_isles"
                language = "en_GB"
                metar_region = "ukwide"

            model["environment"] = {
                "region": environment,
            }

            model["language"] = {
                "default": language,
            }

            model["metar"]["region"] = metar_region

            save_node_model(model)

            return redirect(url_for("timezone_page"))

    return render_template(
        "environment.html",
        model=model,
        error=error,
    )
@app.route("/timezone", methods=["GET", "POST"])
def timezone_page():
    model = load_node_model()
    error = None

    if "timezone" not in model:
        model["timezone"] = {}

    environment = (
        model.get("environment", {})
        .get("region", "british_isles")
    )

    timezones = TIMEZONES.get(environment, {})

    if request.method == "POST":

        timezone = request.form.get("timezone", "").strip()

        if not timezone:
            error = "Please select a time zone."

        elif timezone not in timezones:
            error = "Invalid time zone selection."

        else:
            model["timezone"] = {
                "name": timezone,
            }

            save_node_model(model)

            return redirect(url_for("node_page"))

    return render_template(
        "timezone.html",
        model=model,
        timezones=timezones,
        error=error,
    )
        
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

        ctcss_freq = request.form.get("ctcss_freq")
        if ctcss_freq:
            model["squelch"]["ctcss_freq"] = ctcss_freq
        else:
            model["squelch"]["ctcss_freq"] = None

        model["squelch"]["ctcss_tx"] = (
            request.form.get("ctcss_tx") == "yes"
        )

        save_node_model(model)
        return redirect(url_for("ident_page"))

    return render_template(
        "squelch.html",
        model=model,
        error=error,
        ctcss_frequencies=CTCSS_FREQUENCIES,
    )
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
            return redirect(url_for("cw_page"))

        except ValueError:
            error = "Identification intervals must be numeric."

    return render_template("ident.html", model=model, error=error)

@app.route("/cw", methods=["GET", "POST"])
def cw_page():
    model = load_node_model()
    error = None

    if "cw" not in model:
        model["cw"] = {
            "amp": -10,
            "pitch": 650,
            "cpm": 95,
        }

    if request.method == "POST":
        try:
            cw_amp = int(request.form.get("cw_amp", "-10"))
            cw_pitch = int(request.form.get("cw_pitch", "650"))
            cw_cpm = int(request.form.get("cw_cpm", "95"))
        except ValueError:
            error = "CW settings must be numeric."
        else:
            if cw_amp > -10 or cw_amp < -30:
                error = "CW amplitude must be between -10 and -30 dB."
            elif cw_pitch < 400 or cw_pitch > 1000:
                error = "CW pitch must be between 400 and 1000 Hz."
            elif cw_cpm < 60 or cw_cpm > 160:
                error = "CW speed must be between 60 and 160 CPM."
            else:
                model["cw"] = {
                    "amp": cw_amp,
                    "pitch": cw_pitch,
                    "cpm": cw_cpm,
                }

                save_node_model(model)

                return redirect(url_for("courtesy_page"))

    return render_template(
        "cw.html",
        model=model,
        error=error,
    )
    
@app.route("/courtesy", methods=["GET", "POST"])
def courtesy_page():
    model = load_node_model()
    error = None

    if "courtesy" not in model:
        model["courtesy"] = {
            "mode": "none",
            "frequency": 800,
        }

    node_type = model.get("node", {}).get("type", "simplex")

    if request.method == "POST":
        courtesy_mode = request.form.get("courtesy_mode", "").strip()
        tone_freq = request.form.get("tone_freq", "800").strip()

        if not courtesy_mode:
            error = "Please select a courtesy tone."

        elif node_type == "repeater" and courtesy_mode == "none":
            error = "Repeater systems require a courtesy tone."

        elif courtesy_mode not in ("none", "beep", "morse_t", "morse_k"):
            error = "Invalid courtesy tone selection."

        else:
            try:
                tone_freq = int(tone_freq)
            except ValueError:
                tone_freq = 800

            if tone_freq < 300 or tone_freq > 3000:
                error = "Beep frequency must be between 300 and 3000 Hz."
            else:
                model["courtesy"] = {
                    "mode": courtesy_mode,
                    "frequency": tone_freq,
                }

                save_node_model(model)
                if model.get("node", {}).get("type") == "repeater":
                    return redirect(url_for("repeater_page"))
                return redirect(url_for("modules_page"))

    return render_template(
        "courtesy.html",
        model=model,
        error=error,
    )
@app.route("/repeater", methods=["GET", "POST"])
def repeater_page():
    model = load_node_model()
    error = None

    if "repeater" not in model:
        model["repeater"] = {
            "idle_timeout": 10,
            "sql_timeout": 180,
        }

    if "online_control" not in model:
        model["online_control"] = {
            "enabled": False,
            "command": "998877",
        }

    if request.method == "POST":
        try:
            idle_timeout = int(request.form.get("idle_timeout", "10"))
            sql_timeout = int(request.form.get("sql_timeout", "180"))
        except ValueError:
            error = "Timeout values must be numeric."
        else:
            online_enabled = request.form.get("online_enabled") == "yes"
            online_command = request.form.get("online_command", "").strip()

            if idle_timeout < 1 or idle_timeout > 20:
                error = "Idle timeout must be between 1 and 20 seconds."

            elif sql_timeout < 120 or sql_timeout > 300:
                error = "SQL timeout must be between 120 and 300 seconds."

            elif online_enabled and not (
                online_command.isdigit()
                and len(online_command) == 6
                and online_command[0] in "34567"
            ):
                error = "Online control command must be six digits and begin with 3, 4, 5, 6, or 7."

            else:
                model["repeater"] = {
                    "idle_timeout": idle_timeout,
                    "sql_timeout": sql_timeout,
                }

                model["online_control"] = {
                    "enabled": online_enabled,
                    "command": online_command or "998877",
                }

                save_node_model(model)

                return redirect(url_for("modules_page"))

    return render_template(
        "repeater.html",
        model=model,
        error=error,
    )
    
@app.route("/modules", methods=["GET", "POST"])
def modules_page():
    model = load_node_model()

    if request.method == "POST":
        modules = [
            "ModuleHelp",
            "ModuleParrot",
        ]

        echolink_enabled = request.form.get("module_echolink") == "yes"
        metar_enabled = request.form.get("module_metar") == "yes"

        if echolink_enabled:
            modules.append("ModuleEchoLink")

        if metar_enabled:
            modules.append("ModuleMetarInfo")

        model["modules"]["enabled"] = modules
        model["echolink"]["enabled"] = echolink_enabled
        model["metar"]["enabled"] = metar_enabled

        save_node_model(model)

        if echolink_enabled:
            return redirect(url_for("echolink_page"))

        if metar_enabled:
            return redirect(url_for("metar_default_page"))

        return redirect(url_for("reflector_page"))

    return render_template("modules.html", model=model)

@app.route("/echolink", methods=["GET", "POST"])
def echolink_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        callsign = request.form.get("echolink_callsign", "").strip().upper()
        password = request.form.get("echolink_password", "").strip()
        sysopname = request.form.get("echolink_sysopname", "").strip()
        location_text = request.form.get("echolink_location", "").strip()

        location = f"[Svx] {location_text}"

        if not callsign.endswith(("-L", "-R")):
            error = "EchoLink callsign must end in -L or -R."
        elif not password:
            error = "EchoLink password is required."
        elif not sysopname:
            error = "EchoLink sysop name is required."
        elif not location_text:
            error = "EchoLink location is required."
        elif len(location_text) > 12:
            error = "EchoLink location must be 12 characters or fewer after [Svx]."
        else:
            model["echolink"] = {
                "enabled": True,
                "callsign": callsign,
                "password": password,
                "sysopname": sysopname,
                "location": location,
            }

            save_node_model(model)

            if model["metar"]["enabled"]:
                return redirect(url_for("metar_default_page"))

            return redirect(url_for("reflector_page"))

    return render_template("echolink.html", model=model, error=error)

@app.route("/metar-default", methods=["GET", "POST"])
def metar_default_page():
    model = load_node_model()
    error = None

    if "metar" not in model:
        model["metar"] = {}

    region = model["metar"].get("region") or "ukwide"

    if region not in METAR_REGIONS:
        region = "ukwide"
        model["metar"]["region"] = region
        save_node_model(model)

    airports = METAR_REGIONS[region]

    if request.method == "POST":
        startdefault = request.form.get("startdefault", "").strip().upper()

        if not startdefault:
            error = "Please select a default airport."
        elif startdefault not in airports:
            error = "Selected airport is not valid for this region."
        else:
            model["metar"]["startdefault"] = startdefault
            save_node_model(model)
            return redirect(url_for("metar_airports_page"))

    return render_template(
        "metar_default.html",
        model=model,
        airports=airports,
        error=error,
    )

@app.route("/metar-airports", methods=["GET", "POST"])
def metar_airports_page():
    model = load_node_model()
    error = None

    region = model["metar"].get("region", "ukwide")
    airports = METAR_REGIONS.get(region, {})

    startdefault = model["metar"].get("startdefault", "")

    if request.method == "POST":
        selected_airports = request.form.getlist("airports")

        if len(selected_airports) > 6:
            error = "Please select no more than 6 additional airports."
        else:
            model["metar"]["airports"] = selected_airports
            save_node_model(model)
            return redirect(url_for("reflector_page"))

    return render_template(
        "metar_airports.html",
        model=model,
        airports=airports,
        startdefault=startdefault,
        error=error,
    )
    
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
    if not model.get("dashboard_auth", {}).get("password_hash"):
        return redirect(url_for("setup_auth_page"))
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

@app.route("/setup-auth", methods=["GET", "POST"])
def setup_auth_page():

    model = load_node_model()

    auth = model.get(
        "dashboard_auth",
        {}
    )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not username or not password:

            error = "Username and password are required."

        else:

            model["dashboard_auth"] = {
                "username": username,
                "password_hash": generate_password_hash(password),
            }

            save_node_model(model)

            return redirect("/review")

    return render_template(
        "setup_auth.html",
        auth=auth,
        error=error,
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

@app.route("/status", methods=["GET"])
def status_page():
    model = load_node_model()
    
    system_info = get_system_info()

    status = get_runtime_status(model)
    
    activity = get_reflector_activity()

    environment = model.get(
    "environment",
    {}
).get(
    "region",
    "british_isles"
)

    talkgroups = load_talkgroups(environment)

    return render_template(
        "status.html",
        model=model,
        status=status,
        activity=activity,
        talkgroups=talkgroups,
        system_info=system_info,
    )
@app.route("/authorise", methods=["GET", "POST"])
def authorise_page():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        auth = load_node_model().get(
            "dashboard_auth",
            {}
        )

        stored_user = auth.get("username", "")
        stored_hash = auth.get("password_hash", "")

        if (
            username == stored_user
            and stored_hash
            and check_password_hash(stored_hash, password)
        ):
            session.permanent = True
            session["authorised"] = True

            return redirect(url_for("status_page"))

        error = "Incorrect username or password."

    return render_template(
        "authorise.html",
        error=error,
    )

@app.route("/api/status", methods=["GET"])
def api_status_page():
    model = load_node_model()

    status = get_runtime_status(model)
    activity = get_reflector_activity()
    system_info = get_system_info()

    return jsonify({
        "status": status,
        "activity": activity,
        "system_info": system_info,
    })
@app.route("/talkgroups", methods=["GET", "POST"])
def talkgroups_page():
    if not session.get("authorised"):
        return redirect(url_for("authorise_page"))    
    model = load_node_model()
        

    environment = model.get(
        "environment",
        {}
    ).get(
        "region",
        "british_isles"
    )

    talkgroups = load_talkgroups(environment)

    if request.method == "POST":
        updated = []

        for index in range(len(talkgroups)):
            tg_id = request.form.get(f"id_{index}", "").strip()
            label = request.form.get(f"label_{index}", "").strip()
            colour = request.form.get(f"colour_{index}", "").strip()
            command = request.form.get(f"command_{index}", "").strip()

            if tg_id and label and colour and command:
                updated.append({
                    "id": tg_id,
                    "label": label,
                    "colour": colour,
                    "command": command,
                })

        save_talkgroups(environment, updated)

        return redirect(url_for("status_page"))

    return render_template(
        "talkgroups.html",
        model=model,
        talkgroups=talkgroups,
    )
@app.route("/monitor-tgs", methods=["GET", "POST"])
def monitor_tgs_page():
    if not session.get("authorised"):
        return redirect(url_for("authorise_page"))
    model = load_node_model()
    error = None

    if "reflector" not in model:
        model["reflector"] = {}

    existing = model["reflector"].get("monitor_tg_defs", [])
    selected = model["reflector"].get("monitor_tgs", [])

    monitor_rows = []

    for index in range(6):
        row = existing[index] if index < len(existing) else {}

        tg_id = row.get("id", "")
        label = row.get("label", "")

        monitor_rows.append({
            "id": tg_id,
            "label": label,
            "enabled": tg_id in selected,
        })

    if request.method == "POST":
        updated_defs = []
        updated_selected = []

        for index in range(6):
            tg_id = request.form.get(f"id_{index}", "").strip()
            label = request.form.get(f"label_{index}", "").strip()
            enabled = request.form.get(f"enabled_{index}") == "yes"

            if tg_id or label:
                updated_defs.append({
                    "id": tg_id,
                    "label": label,
                })

            if enabled and tg_id:
                updated_selected.append(tg_id)

        if len(updated_selected) > 6:
            error = "Please select no more than six monitoring talkgroups."
        else:
            model["reflector"]["monitor_tg_defs"] = updated_defs
            model["reflector"]["monitor_tgs"] = updated_selected

            save_node_model(model)

            return redirect(url_for("status_page"))

    return render_template(
        "monitor_tgs.html",
        model=model,
        monitor_rows=monitor_rows,
        error=error,
    )
@app.route("/edit/echolink", methods=["GET", "POST"])
def echolink_edit_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page"))

    model = load_node_model()

    if "echolink" not in model:
        model["echolink"] = {}

    echolink = model["echolink"]

    error = None

    if request.method == "POST":

        echolink["enabled"] = (
            request.form.get("enabled") == "yes"
        )

        echolink["callsign"] = request.form.get(
            "callsign",
            ""
        ).strip().upper()

        echolink["password"] = request.form.get(
            "password",
            ""
        ).strip()

        echolink["sysopname"] = request.form.get(
            "sysopname",
            ""
        ).strip()

        echolink["location"] = request.form.get(
            "location",
            ""
        ).strip()

        save_node_model(model)
        echolink_conf = render_echolink_module(model)

        if echolink_conf:
            write_text_file(
                MODULE_DIR / "ModuleEchoLink.conf",
                echolink_conf
            )
    
        restart_svxlink()
    
        return redirect(url_for("echolink_edit_page"))
    
    return render_template(
                "echolink_edit.html",
                echolink=echolink,
                error=error,
    )
@app.route("/edit/metar", methods=["GET", "POST"])
def metar_edit_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page"))

    model = load_node_model()

    if "metar" not in model:
        model["metar"] = {}

    metar = model["metar"]

    error = None

    if request.method == "POST":

        metar["enabled"] = (
            request.form.get("enabled") == "yes"
        )

        metar["startdefault"] = request.form.get(
            "startdefault",
            ""
        ).strip().upper()

        airports = request.form.get(
            "airports",
            ""
        )

        metar["airports"] = [
            x.strip().upper()
            for x in airports.split(",")
            if x.strip()
        ][:6]

        save_node_model(model)

        metar_conf = render_metar_module(model)

        if metar_conf:
            write_text_file(
                MODULE_DIR / "ModuleMetarInfo.conf",
                metar_conf
            )

        restart_svxlink()

        return redirect(url_for("metar_edit_page"))

    return render_template(
        "metar_edit.html",
        metar=metar,
        error=error,
    )
@app.route("/logout", methods=["GET"])
def logout_page():
    session.pop("authorised", None)
    return redirect(url_for("status_page"))

@app.route("/dtmf", methods=["POST"])
def dtmf_page():
    command = request.form.get("command", "").strip()

    try:
        send_dtmf(command)

    except Exception as exc:
        print(f"DTMF send failed: {exc}")
        return redirect(url_for("status_page"))

    return redirect(url_for("status_page"))
    
if __name__ == "__main__":
    ensure_dirs()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )