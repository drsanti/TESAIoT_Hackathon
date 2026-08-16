# TESAIoT Hackathon

[![Release](https://img.shields.io/badge/release-v0.2.0-0B6E99?style=flat-square)](hex/firmware-manifest.json)
[![Updated](https://img.shields.io/badge/updated-2026--08--16-2E7D32?style=flat-square)](hex/firmware-manifest.json)
[![VSIX](https://img.shields.io/badge/Bitstream%20Studio-0.2.1-5C6BC0?style=flat-square)](vsix/)
[![Firmware](https://img.shields.io/badge/firmware%20HEX-0.2.0-F57C00?style=flat-square)](hex/)
[![Repo](https://img.shields.io/badge/GitHub-TESAIoT__Hackathon-181717?style=flat-square&logo=github)](https://github.com/drsanti/TESAIoT_Hackathon)

Install **Bitstream Studio**, flash the **TESAIoT PSoC Edge DevKit**, and run **live sensor demos** — no firmware or extension build required.

- **Latest VSIX:** Bitstream Studio **0.2.1** (`vsix/bitstream-studio-0.2.1.vsix`)
- **Paired firmware HEX:** **0.2.0** (`hex/tesaiot-bitstream-0.2.0.hex`) — unchanged; 0.2.1 is a host-only update
- **Updated:** 2026-08-16
- **Repository:** [github.com/drsanti/TESAIoT_Hackathon](https://github.com/drsanti/TESAIoT_Hackathon)
- **Video tutorials:**
  - [BitStream Studio](https://www.youtube.com/watch?v=YrEnnaBSxKM&list=PLAnm1xKpsLr4) — install, flash, connect, and demos
  - [AIoT Foundation](https://www.youtube.com/watch?v=Wc_nXiLS864&list=PLOuPSlsBpTYA) — full course playlist

> Use the newest VSIX together with the **`latest`** entry in the firmware manifest. Firmware only needs reflashing when a newer HEX is published.

Watch the YouTube playlists above before or alongside the steps below: [BitStream Studio](https://www.youtube.com/watch?v=YrEnnaBSxKM&list=PLAnm1xKpsLr4) and [AIoT Foundation](https://www.youtube.com/watch?v=Wc_nXiLS864&list=PLOuPSlsBpTYA).

---

## Table of contents

1. [Repository layout](#repository-layout)
2. [Requirements](#requirements)
3. [Quick start](#quick-start)
   - [1. Download this repo](#1-download-this-repo)
   - [2. Install Bitstream Studio](#2-install-bitstream-studio)
   - [3. Flash firmware (hardware labs)](#3-flash-firmware-hardware-labs)
   - [4. Connect your board or simulator](#4-connect-your-board-or-simulator)
   - [5. First-time tips](#5-first-time-tips)
4. [Download only `web-app`](#download-only-web-app)
5. [Web app examples](#web-app-examples)
   - [How to run](#how-to-run)
   - [Example catalog](#example-catalog)
6. [Bitstream vs Simulator](#bitstream-vs-simulator)
7. [Troubleshooting](#troubleshooting)

---

## Repository layout

| Folder                 | Purpose                                                      |
| ---------------------- | ------------------------------------------------------------ |
| [`vsix/`](vsix/)       | Bitstream Studio extension — install in VS Code or Cursor    |
| [`ide/`](ide/)         | BitStream IDE installers (all-in-one app; optional)          |
| [`hex/`](hex/)         | DevKit firmware — flash before hardware labs                 |
| [`flasher/`](flasher/) | TESAIoT Flasher desktop installers (Windows / macOS / Linux) |
| [`web-app/`](web-app/) | Telemetry provider HTML examples (ex01–ex17)                 |

**Not in this GitHub clone** (maintainer-only; listed in [`.gitignore`](.gitignore)): `python-app/`, `ble-react/`, `ble-flet/`. Those BLE teaching apps stay on the maintainer machine and are not part of the published handoff.

---

## Requirements

| Item                                                                       | When you need it                                                             |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [VS Code](https://code.visualstudio.com/) or [Cursor](https://cursor.com/) | Always — to run Bitstream Studio VSIX **or** use [`ide/`](ide/) BitStream IDE |
| **BitStream IDE** (optional)                                               | All-in-one installers in [`ide/`](ide/) — no separate VSIX step              |
| **TESAIoT PSoC Edge DevKit** + USB cable                                   | Hardware labs (**Bitstream** mode)                                           |
| **TESAIoT Flasher** or **ModusToolbox**                                    | To flash firmware from [`hex/`](hex/) — installers in [`flasher/`](flasher/) |
| **Bitstream Simulator** extension (optional)                               | Try the UI **without** a board (**Simulator** mode)                          |

---

## Quick start

### 1. Download this repo

**Option A — Git**

```bash
git clone https://github.com/drsanti/TESAIoT_Hackathon.git
cd TESAIoT_Hackathon
```

**Option B — ZIP** — On GitHub, click **Code → Download ZIP**, then extract the folder.

### 2. Install Bitstream Studio

1. Open [`vsix/`](vsix/) and select the newest **`bitstream-studio-<version>.vsix`** (current: **`0.2.1`**, paired with HEX **`0.2.0`**), or the version your instructor specified.
2. In VS Code or Cursor: **Extensions** → **`…`** → **Install from VSIX…** → select that file.
3. Click **Reload** when prompted.
4. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) → **Open Bitstream Studio**.

More detail: [`vsix/README.md`](vsix/README.md)

**Optional — install from the terminal** (from the repo root; change the version if needed):

```bash
code --install-extension vsix/bitstream-studio-0.2.1.vsix
code -r
```

Use `cursor` instead of `code` if you use Cursor. To replace an older install first:

```bash
code --uninstall-extension TERNIONDEV.bitstream-studio
```

### 3. Flash firmware (hardware labs)

1. Open [`hex/`](hex/) and pick the newest **`tesaiot-bitstream-<version>.hex`** (current: **`tesaiot-bitstream-0.2.0.hex`**, which pairs with VSIX **0.2.1**).
2. Flash the board with **TESAIoT Flasher** ([`flasher/`](flasher/)) or **ModusToolbox**.
3. If no serial port appears, unplug and replug the USB cable.

More detail: [`hex/README.md`](hex/README.md)

### 4. Connect your board or simulator

1. In Bitstream Studio, choose **Bitstream** (real DevKit) or **Simulator** (no hardware).
2. For **Bitstream**: select your **COM** port and set baud rate to **921600**.
3. Open **Sensor Telemetry** or **Sensor Studio** and confirm readings update.

Bitstream Studio starts its background services when the extension loads — nothing else to install for normal use.

### 5. First-time tips

| Goal                      | What to do                                                                              |
| ------------------------- | --------------------------------------------------------------------------------------- |
| **3D models in the UI**   | Command Palette → **Download Free Assets from GitHub**                                  |
| **Blank or frozen panel** | Command Palette → **Bitstream Studio: Reload Webview**, or **Developer: Reload Window** |

---

## Download only `web-app`

If you already have Bitstream Studio installed (or will get the VSIX another way) and only need the HTML telemetry examples, use a **sparse clone** so Git does not download `vsix/`, `hex/`, or other large handoff folders:

```bash
git clone --filter=blob:none --sparse https://github.com/drsanti/TESAIoT_Hackathon.git
cd TESAIoT_Hackathon
git sparse-checkout set web-app
```

| Step | Purpose |
| ---- | ------- |
| `--filter=blob:none` | Partial clone — file contents download only when needed |
| `--sparse` | Start with a sparse working tree (usually root files only) |
| `git sparse-checkout set web-app` | Check out [`web-app/`](web-app/) and everything under it |

**Optional — shallower clone** (history tip only):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/drsanti/TESAIoT_Hackathon.git
cd TESAIoT_Hackathon
git sparse-checkout set web-app
```

Notes:

- Root files such as `README.md` may still appear; that is normal.
- Large **VSIX** / **HEX** (Git LFS) artifacts stay out of the working tree.
- To serve the examples, point Bitstream Studio’s **Serve Web App Folder over HTTP** at the local `web-app/` folder (see below).

---

## Web app examples

The [`web-app/`](web-app/) folder has HTML pages that display **live sensor data** while Bitstream Studio is running on your computer.

### How to run

1. Complete steps 2 and 4 above (extension installed, telemetry connected).
2. For MQTT examples (ex09–ex15): toolbar **Server** → **Start broker**.
3. Command Palette → **Serve Web App Folder over HTTP** → select the **`web-app`** folder from this repo.
4. Click the link in the notification, or open **`index.html`** from that served URL.
5. Choose an example from the list.

Open [`web-app/index.html`](web-app/index.html) in the served site for the full catalog and short instructions.

Hackathon participants use **Bitstream Studio** (UART / Simulator / BLE host in the extension) plus these **web-app** pages. Standalone BLE lab trees (`python-app`, `ble-react`, `ble-flet`) are **not** published here.

### Example catalog

| Page                                                                  | Sensors / topic                                |
| --------------------------------------------------------------------- | ---------------------------------------------- |
| [ex01 — SHT40](web-app/ex01_sht40.html)                               | Temperature and humidity                       |
| [ex02 — DPS368](web-app/ex02_dps368.html)                             | Pressure and temperature                       |
| [ex03 — BMM350](web-app/ex03_bmm350.html)                             | Magnetometer and compass                       |
| [ex04 — BMI270 IMU](web-app/ex04_bmi270_imu.html)                     | Accelerometer and gyro                         |
| [ex05 — BMI270 horizon](web-app/ex05_bmi270_orientation.html)         | Artificial horizon                             |
| [ex16 — ADC_POT](web-app/ex16_adc_pot.html)                           | POT1–POT4 millivolts                           |
| [ex17 — SW_BTN](web-app/ex17_sw_btn.html)                             | SW0 / SW5 / SW6 state + press counts           |
| [ex06 — Dashboard](web-app/ex06_dashboard.html)                       | All six sensors (IMU, env, pots, switches)     |
| [ex07 — Catalog browser](web-app/ex07_catalog_browser.html)           | Browse sensor catalog                          |
| [ex08 — Stale / route](web-app/ex08_stale_and_route.html)             | Connection status demo                         |
| [ex09 — MQTT subscriber](web-app/ex09_mqtt_subscriber.html)           | MQTT broker smoke test (`ws://127.0.0.1:8883`) |
| [ex10 — MQTT publisher](web-app/ex10_mqtt_publisher.html)             | Publish lab JSON to `sensors/lab/temp`         |
| [ex11 — MQTT wildcards](web-app/ex11_mqtt_wildcards.html)             | `sensors/+/temp` and `sensors/#` filter log    |
| [ex12 — DevKit gauges](web-app/ex12_mqtt_devkit_gauges.html)          | Parse MQTT `channels` payload to gauge cards   |
| [ex13 — LiveDataClient MQTT](web-app/ex13_mqtt_live_data_client.html) | SDK connect, subscribe, and publish            |
| [ex14 — QoS & retain](web-app/ex14_mqtt_qos_retain.html)              | QoS 0/1/2 and retain flag lab                  |
| [ex15 — WS vs MQTT dashboard](web-app/ex15_ws_mqtt_dashboard.html)    | Switch `:9998` WebSocket bus vs `:8883` MQTT   |

---

## Bitstream vs Simulator

| Mode          | Use this when                                                              |
| ------------- | -------------------------------------------------------------------------- |
| **Bitstream** | Your DevKit is plugged in and firmware from [`hex/`](hex/) is flashed      |
| **Simulator** | You have no board — install the separate **Bitstream Simulator** extension |

Use one mode at a time. Switching modes clears old sample data.

---

## Troubleshooting

| Problem                          | What to try                                                                                                                 |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **VSIX will not install**        | Use VS Code 1.85+ or a current Cursor build; download the VSIX again                                                        |
| **Bitstream panel is blank**     | Reload the webview or reload the window; check the extension is enabled                                                     |
| **No COM port**                  | Re-flash firmware; try another USB port or cable; on Windows, install the KitProg3 driver                                   |
| **Linux: board not listed**      | Replug USB; **Refresh** in the flasher; udev rules for KitProg3 — see [`flasher/README.md`](flasher/README.md)              |
| **Port open but no sensor data** | Toolbar set to **Bitstream**; baud **921600**; VSIX and firmware versions match                                             |
| **Web examples show no data**    | Bitstream Studio is open; board or simulator connected; you used **Serve Web App Folder over HTTP** on the `web-app` folder |
| **Missing 3D models**            | Command Palette → **Download Free Assets from GitHub**                                                                      |

Step-by-step help: [`vsix/README.md`](vsix/README.md) · [`hex/README.md`](hex/README.md) · [`flasher/README.md`](flasher/README.md)
