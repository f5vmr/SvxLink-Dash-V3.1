#!/usr/bin/env python3

"""
Primary SvxLink configuration renderer for SvxLink-Dash-V3.
"""

from renderers.template_engine import render_config_template
import platform

# =========================================================
# System information
# =========================================================
import platform


def get_library_path():
    machine = platform.machine()

    if machine in ("armv7l", "armhf"):
        return "/usr/lib/arm-linux-gnueabihf/svxlink"

    if machine in ("aarch64", "arm64"):
        return "/usr/lib/aarch64-linux-gnu/svxlink"

    if machine in ("x86_64", "amd64"):
        return "/usr/lib/x86_64-linux-gnu/svxlink"

    return "/usr/lib/svxlink"

# =========================================================
# Module rendering
# =========================================================

def build_modules(model):
    """
    Render MODULES= line content.
    """

    enabled = model.get("modules", {}).get("enabled", [])

    return ",".join(enabled)
# =========================================================
# Language rendering
# =========================================================
def get_default_language(model):
    """
    Return selected default language.

    Set by /environment page.
    British Isles and Australia/NZ use en_GB.
    North America uses en_US.
    """

    return (
        model.get("language", {}).get("default")
        or model.get("node", {}).get("language")
        or "en_GB"
    )
# =========================================================
# Module-specific renderers
# =========================================================

def render_echolink_module(model):
    """
    Render ModuleEchoLink section if enabled.
    """

    echolink = model.get("echolink", {})

    if not echolink.get("enabled"):
        return ""

    return render_config_template(
        "module_echolink.template",
        {
            "ECHOLINK_CALLSIGN": echolink.get("callsign", ""),
            "ECHOLINK_PASSWORD": echolink.get("password", ""),
            "ECHOLINK_SYSOPNAME": echolink.get("sysopname", ""),
            "ECHOLINK_LOCATION": echolink.get("location", ""),
            "DEFAULT_LANG": get_default_language(model),
        }
    )

# =========================================================
# METAR rendering
# =========================================================
def render_metar_module(model):
    """
    Render ModuleMetarInfo section if enabled.

    STARTDEFAULT must always contain a valid ICAO.
    AIRPORTS includes STARTDEFAULT first, followed by up to six extras.
    """

    metar = model.get("metar", {})

    if not metar.get("enabled"):
        return ""

    startdefault = metar.get("startdefault", "").strip().upper()
    extras = metar.get("airports", [])

    airports = []

    if startdefault:
        airports.append(startdefault)

    for airport in extras:
        airport = airport.strip().upper()
        if airport and airport not in airports:
            airports.append(airport)

    return render_config_template(
        "module_metar.template",
        {
            "METAR_STARTDEFAULT": startdefault,
            "METAR_AIRPORTS": ",".join(airports),
        }
    )
# =========================================================
# Ident rendering
# =========================================================

def ident_enabled(mode, ident_type):
    """
    Determine voice/cw enable flags.

    mode:
        none
        cw
        voice
        both

    ident_type:
        voice
        cw
    """

    if mode == "both":
        return 1

    if mode == ident_type:
        return 1

    return 0


# =========================================================
# Online control block
# =========================================================

def render_online_control(model):
    """
    Render ONLINE control block if enabled.
    """

    online = model.get("online_control", {})

    if not online.get("enabled"):
        return ""

    cmd = online.get("command")

    return (
        f"ONLINE_CMD={cmd}\n"
        "ONLINE=1"
    )


# =========================================================
# CTCSS helpers
# =========================================================

def render_report_ctcss(model):
    """
    Render REPORT_CTCSS line if required.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") != ("ctcss"):
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return f"REPORT_CTCSS={freq}"


def render_tx_ctcss_logic(model):
    """
    Render TX_CTCSS logic line if TX CTCSS enabled.
    """

    squelch = model.get("squelch", {})

    if not squelch.get("ctcss_tx"):
        return ""

    mode = model.get("tx_ctcss_mode", "ALWAYS")

    return f"TX_CTCSS={mode}"

def render_open_on_ctcss_line(model):
    """
    Render OPEN_ON_CTCSS for repeater logic only when CTCSS is used.

    For non-CTCSS squelch methods, leave it commented.
    """

    node_type = model.get("node", {}).get("type")
    squelch = model.get("squelch", {})

    if node_type != "repeater":
        return "#OPEN_ON_CTCSS=1000"

    if squelch.get("method") != ("ctcss"):
        return "#OPEN_ON_CTCSS=1000"

    if not squelch.get("ctcss_freq"):
        return "#OPEN_ON_CTCSS=1000"

    return "OPEN_ON_CTCSS=1000"

# =========================================================
# RX rendering
# =========================================================

def render_rx_sql_block(model):
    """
    Render SQL_DET line.
    """

    interface = model.get("interface", {})
    squelch = model.get("squelch", {})

    interface_mode = interface.get("mode")
    squelch_method = squelch.get("method")

    if interface_mode == "hidraw":
        return "SQL_DET=HIDRAW"

    if interface_mode == "hybrid":
        if squelch_method == "ctcss":
            return "SQL_DET=CTCSS"

        return "SQL_DET=GPIOD"
    if squelch_method == "gpiod_ctcss":
        return "\n".join([
            "SQL_DET=COMBINE",
            "SQL_COMBINE=(Rx1:CTCSS)&(Rx1:GPIOD)",
        ])
    if squelch_method == "ctcss":
        return "SQL_DET=CTCSS"
    if squelch_method == "serial":
        return "SQL_DET=SERIAL"
    if squelch_method == "serial_ctcss":
        return "\n".join([
        "SQL_DET=COMBINE",
        "SQL_COMBINE=(Rx1:CTCSS)&(Rx1:SERIAL)",
        ])
    return "SQL_DET=GPIOD"


def render_rx_ctcss_block(model):
    """
    Render CTCSS RX block.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") != ("ctcss"):
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        "CTCSS_MODE=4",
        f"CTCSS_FQ={freq}",
        "#CTCSS_SNR_OFFSET=0",
        "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
        "#CTCSS_OPEN_THRESH=15",
        "#CTCSS_CLOSE_THRESH=9",
        "#CTCSS_BPF_LOW=60",
        "#CTCSS_BPF_HIGH=270",
        "#CTCSS_EMIT_TONE_DETECTED=0",
    ])


def render_rx_gpiod_block(model):
    """
    Render RX GPIOD block.
    """
    interface = model.get("interface", {})

    if interface.get("mode") == "hidraw":
        return ""
    if model.get("squelch", {}).get("method") == "gpiod_ctcss":
        return ""    
    if interface.get("sql_source") != "gpiod":
        return ""

    gpio = model.get("gpio", {}).get("sql", {})

    chip = gpio.get("chip", "gpiochip0")
    line = str(gpio.get("line", 203))

    if gpio.get("invert"):
            line = f"!{line}"

    return "\n".join([
        f"SQL_GPIOD_CHIP={chip}",
        f"SQL_GPIOD_LINE={line}",
    ])


def render_rx_hidraw_block(model):
    """
    Render RX HIDRAW block.
    """

    interface = model.get("interface", {})

    if interface.get("sql_source") != "hidraw":
        return ""

    hid = model.get("hidraw", {})

    device = hid.get("device", "/dev/hidraw0")
    pin = hid.get("sql_pin", "VOL_DN")
    if hid.get("sql_invert"):
        pin = f"!{pin}"

    return "\n".join([
        f"HID_DEVICE={device}",
        f"HID_SQL_PIN={pin}",
    ])
def render_rx_combine_sections(model):
    """
    Render COMBINE detector subsections.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") == "gpiod_ctcss":
        return "\n\n".join([
            render_rx_ctcss_combine_block(model),
            render_rx_gpiod_combine_block(model),
        ])

    if squelch.get("method") == "serial_ctcss":
        return "\n\n".join([
            render_rx_ctcss_combine_block(model),
            render_rx_serial_combine_block(model),
        ])
    return ""


def render_rx_ctcss_combine_block(model):
    squelch = model.get("squelch", {})
    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        "[Rx1:CTCSS]",
        "SQL_DET=CTCSS",
        "CTCSS_MODE=4",
        f"CTCSS_FQ={freq}",
        "#CTCSS_SNR_OFFSET=0",
        "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
        "#CTCSS_OPEN_THRESH=15",
        "#CTCSS_CLOSE_THRESH=9",
        "#CTCSS_BPF_LOW=60",
        "#CTCSS_BPF_HIGH=270",
        "#CTCSS_EMIT_TONE_DETECTED=0",
    ])
def render_rx_gpiod_combine_block(model):
    gpio = model.get("gpio", {}).get("sql", {})

    chip = gpio.get("chip", "gpiochip0")
    line = gpio.get("line", 203)

    return "\n".join([
        "[Rx1:GPIOD]",
        "SQL_DET=GPIOD",
        f"SQL_GPIOD_CHIP={chip}",
        f"SQL_GPIOD_LINE={line}",
    ])
def render_rx_serial_block(model):
    """
    Render RX SERIAL squelch block.
    """

    if model.get("squelch", {}).get("method") != "serial":
        return ""

    serial = model.get("serial", {})

    return "\n".join([
        "SERIAL_PORT=" + serial.get("sql_port", "/dev/ttyS0"),
        "SERIAL_PIN=" + serial.get("sql_pin", "CTS"),
        "SERIAL_SET_PINS=" + serial.get("sql_set_pins", "DTR!RTS"),
    ])
def render_rx_serial_combine_block(model):
    """
    Render RX SERIAL subsection for COMBINE squelch.
    """

    serial = model.get("serial", {})

    return "\n".join([
        "[Rx1:SERIAL]",
        "SQL_DET=SERIAL",
        "SERIAL_PORT=" + serial.get("sql_port", "/dev/ttyS0"),
        "SERIAL_PIN=" + serial.get("sql_pin", "CTS"),
        "SERIAL_SET_PINS=" + serial.get("sql_set_pins", "DTR!RTS"),
    ])
# =========================================================
# TX rendering
# =========================================================

def render_tx_ptt_block(model):
    """
    Render TX PTT block.
    """

    interface = model.get("interface", {})
    ptt_source = interface.get("ptt_source")

    if ptt_source == "hidraw":

        hid = model.get("hidraw", {})

        device = hid.get("device", "/dev/hidraw0")
        pin = hid.get("ptt_pin", "GPIO3")

        return "\n".join([
            "PTT_TYPE=Hidraw",
            f"HID_DEVICE={device}",
            f"HID_PTT_PIN={pin}",
        ])

    gpio = model.get("gpio", {}).get("ptt", {})

    chip = gpio.get("chip", "gpiochip0")
    line = gpio.get("line", 6)

    if ptt_source == "serial":

        serial = model.get("serial", {})

        return "\n".join([
            "PTT_TYPE=SerialPin",
            "PTT_PORT=" + serial.get("ptt_port", "/dev/ttyS0"),
            "PTT_PIN=" + serial.get("ptt_pin", "DTRRTS"),
        ])
    return "\n".join([
        "PTT_TYPE=GPIOD",
        f"PTT_GPIOD_CHIP={chip}",
        f"PTT_GPIOD_LINE={line}",
    ])


def render_tx_ctcss_block(model):
    """
    Render TX-side CTCSS block.
    """

    squelch = model.get("squelch", {})

    if not squelch.get("ctcss_tx"):
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        f"CTCSS_FQ={freq}",
        "CTCSS_LEVEL=-24",
    ])


# =========================================================
# Macros
# =========================================================

def render_macros(model):
    """
    Render reflector macro section.
    """

    reflector = model.get("reflector", {})

    if not reflector.get("enabled"):
        return "[Macros]"

    host = reflector.get("host", "")

    if "uk.wide" in host or "yorkshire" in host:

        macro_lines = "\n".join([
            "1=::91235#",
            "2=::912350#",
            "6=::9123561#",
            "9=::910#",
        ])

    elif "australia" in host:

        macro_lines = "\n".join([
            "1=::9505#",
            "9=::910#",
        ])

    elif "north.america" in host:

        macro_lines = "\n".join([
            "1=::93100#",
            "9=::910#",
        ])

    else:
        macro_lines = ""

    return render_config_template(
        "macros.template",
        {
            "MACRO_LINES": macro_lines,
        }
    )


# =========================================================
# Logic rendering
# =========================================================

def render_active_logic(model):
    """
    Render SimplexLogic or RepeaterLogic.
    """

    node_type = model.get("node", {}).get("type")

    short_ident = model.get("ident", {}).get("short", {})
    long_ident = model.get("ident", {}).get("long", {})

    values = {
        "MODULES": build_modules(model),
        "CALLSIGN": model["node"]["callsign"],

        "SHORT_IDENT_INTERVAL": short_ident.get("interval", 15),
        "SHORT_VOICE_ID_ENABLE": ident_enabled(
            short_ident.get("mode"),
            "voice"
        ),
        "SHORT_CW_ID_ENABLE": ident_enabled(
            short_ident.get("mode"),
            "cw"
        ),

        "LONG_IDENT_INTERVAL": long_ident.get("interval", 60),
        "LONG_VOICE_ID_ENABLE": ident_enabled(
            long_ident.get("mode"),
            "voice"
        ),
        "LONG_CW_ID_ENABLE": ident_enabled(
            long_ident.get("mode"),
            "cw"
        ),

        "TIME_FORMAT": model.get("time_format", "24"),

        "CW_AMP": model.get("cw", {}).get("amp", -10),
        "CW_PITCH": model.get("cw", {}).get("pitch", 650),
        "CW_CPM": model.get("cw", {}).get("cpm", 95),

        "DEFAULT_LANG": get_default_language(model),

        "RGR_SOUND_ALWAYS": model.get("courtesy", {}).get("mode") != "none" and 1 or 0,

        "REPORT_CTCSS_LINE": render_report_ctcss(model),
        "TX_CTCSS_LINE": render_tx_ctcss_logic(model),

        "FX_GAIN_NORMAL": model.get("fx_gain_normal", 0),
        "FX_GAIN_LOW": model.get("fx_gain_low", -12),

        "ONLINE_CONTROL_BLOCK": render_online_control(model),

        "IDLE_TIMEOUT": model.get("idle_timeout", 10),
        "OPEN_ON_CTCSS_LINE": render_open_on_ctcss_line(model),
        "REPEATER_SQL_TIMEOUT": model.get("sql_timeout", 180),
    }

    if node_type == "repeater":
        return render_config_template(
            "repeater_logic.template",
            values
        )

    return render_config_template(
        "simplex_logic.template",
        values
    )


# =========================================================
# Reflector rendering
# =========================================================

def render_reflector_logic(model):
    """
    Render ReflectorLogic section if enabled.
    """

    reflector = model.get("reflector", {})

    if not reflector.get("enabled"):
        return ""

    host = reflector.get("host", "")

    monitor_tgs = reflector.get(
        "monitor_tgs",
        []
)

    if isinstance(monitor_tgs, list):
        monitor_tgs = ",".join(
            str(x) for x in monitor_tgs
    )

    if not monitor_tgs:
        monitor_tgs = "0"

    return render_config_template(
        "reflector_logic.template",
        {
            "REFLECTOR_HOST": reflector["host"],
            "REFLECTOR_PORT": reflector["port"],
            "CALLSIGN": model["node"]["callsign"],
            "REFLECTOR_AUTH_KEY": reflector["auth_key"],
            "MONITOR_TGS": monitor_tgs,
            "TG_SELECT_TIMEOUT": model.get("tg_timeout", 60),
            "DEFAULT_LANG": get_default_language(model),
        }
    )


def render_link_to_reflector(model):
    """
    Render LinkToReflector section if enabled.
    """

    reflector = model.get("reflector", {})

    if not reflector.get("enabled"):
        return ""

    node_type = model.get("node", {}).get("type")

    logic_name = (
        "RepeaterLogic"
        if node_type == "repeater"
        else "SimplexLogic"
    )

    return render_config_template(
        "link_to_reflector.template",
        {
            "ACTIVE_LOGIC_NAME": logic_name,
        }
    )


# =========================================================
# Final configuration renderer
# =========================================================

def render_svxlink_config(model):
    """
    Render final svxlink.conf text.
    """

    node_type = model.get("node", {}).get("type")

    logic_name = (
        "RepeaterLogic"
        if node_type == "repeater"
        else "SimplexLogic"
    )
    logics = logic_name

    if model.get("reflector", {}).get("enabled"):
        logics = f"{logic_name},ReflectorLogic"
        
    reflector_enabled = model.get("reflector", {}).get("enabled")

    links_line = (
        "LINKS=LinkToReflector"
        if reflector_enabled
        else "#LINKS=LinkToReflector"
    )

    values = {
        "LOGIC_CORE_PATH": get_library_path(),
        "LOGICS": logics,
        "LINKS_LINE": links_line,

        "ACTIVE_LOGIC_SECTION": render_active_logic(model),

        "REFLECTOR_LOGIC_SECTION": render_reflector_logic(model),

        "LINK_TO_REFLECTOR_SECTION": render_link_to_reflector(model),

        "RX_SQL_BLOCK": render_rx_sql_block(model),
        "RX_CTCSS_BLOCK": render_rx_ctcss_block(model),
        "RX_GPIOD_BLOCK": render_rx_gpiod_block(model),
        "RX_HIDRAW_BLOCK": render_rx_hidraw_block(model),
        "RX_SERIAL_BLOCK": render_rx_serial_block(model),
        "RX_COMBINE_SECTIONS": render_rx_combine_sections(model),

        "TX_PTT_BLOCK": render_tx_ptt_block(model),
        "TX_CTCSS_BLOCK": render_tx_ctcss_block(model),

        "SQL_HANGTIME": model.get("sql_hangtime", 20),
        "SQL_TAIL_ELIM": model.get("sql_tail_elim", 270),

        "MACROS_SECTION": render_macros(model),
    }

    return render_config_template(
        "svxlink.conf.template",
        values
    )