#!/usr/bin/env python3
"""
PC Dashboard Server (Windows)
Об'єднує дані з Glances API (CPU/GPU/RAM/мережа) та LibreHardwareMonitor
(вентилятори, температури плати) в єдиний JSON для показу на телефоні.

Запуск:  python pc_dashboard_server.py
Порт 8080, доступний з мережі (0.0.0.0).
"""

import json
import os
import re
import time
from urllib.request import urlopen

from flask import Flask, jsonify, Response, send_file

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLANCES_URL = "http://localhost:61208/api/4"
LHM_URL = "http://localhost:8085/data.json"
SENSOR_CONFIG_PATH = os.path.join(BASE_DIR, "sensor_config.json")


def load_sensor_config():
    if not os.path.exists(SENSOR_CONFIG_PATH):
        print(f"Файл {SENSOR_CONFIG_PATH} не знайдено. Продовжую без датчиків плати.")
        return {}
    with open(SENSOR_CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


SENSORS = load_sensor_config()
NETWORK_INTERFACE = SENSORS.get("network_interface", "Ethernet")
CACHE_TTL = 1.0
_cache = {"data": None, "ts": 0}
_lhm_cache = {"flat": None, "ts": 0}


def http_json(url, timeout=2):
    try:
        with urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8-sig"))
    except Exception:
        return None


_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def parse_value(text):
    """'29,0 °C' -> 29.0 ; '1 035 RPM' -> 1035.0"""
    s = (text or "").replace("\u00a0", " ")
    s = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", s)
    m = _NUM.search(s)
    return float(m.group(0).replace(",", ".")) if m else None


def flatten(node, path, out):
    """Збирає листки дерева LHM у словник {(chip, group, label): число}."""
    path = path + [node.get("Text", "")]
    children = node.get("Children") or []
    if not children:
        if node.get("Value") and len(path) >= 3:
            val = parse_value(node["Value"])
            if val is not None:
                out[(path[-3], path[-2], path[-1])] = val
        return
    for child in children:
        flatten(child, path, out)


def fetch_lhm_flat():
    now = time.time()
    if _lhm_cache["flat"] is not None and (now - _lhm_cache["ts"]) < CACHE_TTL:
        return _lhm_cache["flat"]
    tree = http_json(LHM_URL)
    if tree is None:
        return None
    flat = {}
    flatten(tree, [], flat)
    _lhm_cache["flat"] = flat
    _lhm_cache["ts"] = now
    return flat


def get_sensor_value(ref):
    """ref = {"chip", "group", "label"} -> число або None."""
    if not ref:
        return None
    flat = fetch_lhm_flat()
    if flat is None:
        return None
    val = flat.get((ref.get("chip"), ref.get("group"), ref.get("label")))
    return round(val, 1) if val is not None else None


def get_fan_percent(fan_ref):
    """% від реальних обертів: (RPM - MIN) / (MAX - MIN) * 100"""
    if not fan_ref:
        return None
    rpm = get_sensor_value(fan_ref)
    if rpm is None:
        return None
    min_rpm = fan_ref.get("min_rpm", 0)
    max_rpm = fan_ref.get("max_rpm", 100)
    if max_rpm <= min_rpm:
        return None
    return round(max(0, min(100, (rpm - min_rpm) / (max_rpm - min_rpm) * 100)), 1)


def fetch_glances(endpoint):
    return http_json(f"{GLANCES_URL}/{endpoint}")


def collect_data():
    data = {
        "timestamp": time.time(),
        "cpu": {"load_percent": None, "temp_c": None, "fan_percent": None},
        "gpu": {"load_percent": None, "temp_c": None, "fan_percent": None, "vram_percent": None, "name": None},
        "ram": {"used_percent": None},
        "board": {"vrm_temp_c": None, "pch_temp_c": None},
        "case_fans": [],
        "network": {"down_mbps": None, "up_mbps": None},
    }

    cpu = fetch_glances("cpu")
    if cpu:
        data["cpu"]["load_percent"] = round(cpu.get("total", 0), 1)
    data["cpu"]["temp_c"] = get_sensor_value(SENSORS.get("cpu_temp"))
    data["cpu"]["fan_percent"] = get_fan_percent(SENSORS.get("cpu_fan"))

    gpu_list = fetch_glances("gpu")
    if gpu_list:
        gpu = gpu_list[0]
        data["gpu"]["name"] = gpu.get("name")
        data["gpu"]["load_percent"] = gpu.get("proc")
        data["gpu"]["temp_c"] = gpu.get("temperature")
        data["gpu"]["fan_percent"] = gpu.get("fan_speed")
        data["gpu"]["vram_percent"] = round(gpu.get("mem", 0), 1) if gpu.get("mem") is not None else None

    mem = fetch_glances("mem")
    if mem:
        data["ram"]["used_percent"] = round(mem.get("percent", 0), 1)

    data["board"]["vrm_temp_c"] = get_sensor_value(SENSORS.get("vrm_temp"))
    data["board"]["pch_temp_c"] = get_sensor_value(SENSORS.get("pch_temp"))

    data["case_fans"] = [
        {"label": fan.get("display_label", fan.get("label", "Case Fan")), "percent": get_fan_percent(fan)}
        for fan in SENSORS.get("case_fans", [])
    ]

    net_list = fetch_glances("network")
    if net_list:
        for iface in net_list:
            if iface.get("interface_name") == NETWORK_INTERFACE:
                recv_bps = iface.get("bytes_recv_rate_per_sec", 0) or 0
                sent_bps = iface.get("bytes_sent_rate_per_sec", 0) or 0
                data["network"]["down_mbps"] = round(recv_bps * 8 / 1_000_000, 2)
                data["network"]["up_mbps"] = round(sent_bps * 8 / 1_000_000, 2)
                break

    return data


@app.route("/data")
def get_data():
    now = time.time()
    if _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
        _cache["data"] = collect_data()
        _cache["ts"] = now
    return jsonify(_cache["data"])


@app.route("/")
def index():
    html_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(html_path):
        return send_file(html_path)
    return Response(
        "<h3>index.html не знайдено</h3><p>Дані доступні тут: <a href='/data'>/data</a></p>",
        mimetype="text/html",
    )


if __name__ == "__main__":
    port = 8080
    print("=" * 50)
    print("PC Dashboard Server (Windows)")
    print(f"Дані: http://<IP-цього-ПК>:{port}/data")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)