#!/usr/bin/env python3

import subprocess


def run_nmcli(args):
    result = subprocess.run(
        ["sudo", "-n", "nmcli"] + args,
        text=True,
        capture_output=True,
    )

    output = []

    if result.stdout:
        output.extend(result.stdout.strip().splitlines())

    if result.stderr:
        output.extend(result.stderr.strip().splitlines())

    return output

def wifi_scan():
    run_nmcli(["dev", "wifi", "rescan"])
    return run_nmcli(["dev", "wifi", "list"])


def connection_list():
    return run_nmcli(["con", "show", "--order", "type"])


def wifi_status():
    return run_nmcli(["radio"])


def wifi_on():
    run_nmcli(["radio", "wifi", "on"])
    return run_nmcli(["radio", "wifi"])

def switch_wifi(ssid):
    output = []

    output += run_nmcli([
        "con",
        "modify",
        ssid,
        "connection.autoconnect",
        "yes",
    ])

    output += run_nmcli([
        "con",
        "up",
        ssid,
    ])

    return output


def delete_wifi(ssid):
    return run_nmcli([
        "con",
        "delete",
        ssid,
    ])
def hotspot_status():
    return run_nmcli([
        "-t",
        "-f",
        "NAME,TYPE,DEVICE",
        "connection",
        "show",
        "--active",
    ])

def connect_wifi(ssid, password):
    return run_nmcli([
        "dev",
        "wifi",
        "connect",
        ssid,
        "password",
        password,
    ])
    
def start_hotspot():
    return run_nmcli([
        "connection",
        "up",
        "Hotspot",
    ])


def stop_hotspot():
    return run_nmcli([
        "connection",
        "down",
        "Hotspot",
    ])
