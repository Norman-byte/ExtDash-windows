# ExtDash Windows

[Українська](README.uk.md) | **English**

Author: [Norman-byte](https://github.com/Norman-byte)

Created in collaboration with [Claude](https://claude.ai) (Anthropic).

Phone-friendly PC monitoring dashboard for Windows. A small Flask server merges data from
Glances (CPU load, GPU, RAM, network) and LibreHardwareMonitor (CPU temperature, fans,
motherboard temperatures) into one JSON, and serves a single-page dashboard (`index.html`).

## Requirements

- Windows 10/11
- Python 3 with Flask and Glances (web mode): `pip install flask "glances[web]"`
- LibreHardwareMonitor (LHM): `winget install LibreHardwareMonitor.LibreHardwareMonitor`

## LibreHardwareMonitor setup

1. Start LHM (as administrator, otherwise board sensors may be unreadable).
2. Options -> Remote Web Server -> enable (port 8085).
3. Options -> Run On Windows Startup.

The server reads `http://127.0.0.1:8085/data.json`.

## Sensor config

Copy `sensor_config.example.json` to `sensor_config.json` and edit it. The file is listed
in `.gitignore`, because it is specific to each PC. Each sensor is a reference to a leaf in
the LHM tree: `chip` / `group` / `label` must match the names shown in LHM exactly.

- `cpu_fan`, `case_fans`: fan sensors, shown as percent
- `cpu_temp`, `vrm_temp`, `pch_temp`: temperature sensors
- `gpu_temp`: optional, replaces the GPU temperature from Glances (for example GPU Hot Spot)
- `network_interface`: interface name as reported by Glances

Fans: `label` is the sensor name in LHM, `display_label` is the text shown on the dashboard.
Fan percent is `(RPM - min_rpm) / (max_rpm - min_rpm) * 100`, so set `min_rpm` and `max_rpm`
to the real range of each fan.

## Running

Start Glances first, then the server:

    glances -w --disable-plugin smart
    cd C:\path\to\ExtDash-windows
    python pc_dashboard_server.py

Open `http://127.0.0.1:8080` on the PC or `http://<PC-IP>:8080` on the phone.
Raw JSON is at `/data`. Right after start some values may be `null` for a few seconds.
After changing the server code or `sensor_config.json`, restart the server.

## Autostart

Run both commands at logon with Task Scheduler (a script with two Start-Process calls,
Glances first, the server 5 seconds later), with a 30 second logon delay.

## Security

Glances, LHM and the server listen on all interfaces without authentication, so the
metrics are visible to everyone on the local network.

## License

See `LICENSE`.