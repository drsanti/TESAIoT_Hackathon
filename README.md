# TESAIoT Hackathon

Handoff bundle for the TESAIoT hackathon: **Bitstream Studio** extension, **firmware HEX**, and **live-data web examples**.

Repository: [github.com/drsanti/TESAIoT_Hackathon](https://github.com/drsanti/TESAIoT_Hackathon)

## Layout

| Path | Role |
|------|------|
| `vsix/` | Bitstream Studio `.vsix` — `bitstream-studio-<version>.vsix` (matches `extension/package.json`) |
| `hex/` | Firmware `.hex` — `tesaiot-bitstream-<version>.hex` (same version label) |
| `web-app/` | Static HTML dashboards (serve this folder over HTTP) |
| `web-app/index.html` | Example catalog |
| `web-app/shared/` | `ex-demo.css`, `ex-demo.js` (ex02–ex08) |

## Quick start (participants)

1. **Clone** this repo.
2. **Install extension** — VS Code → Extensions → `…` → **Install from VSIX…** → pick the file in `vsix/`.
3. **Flash firmware** — program the board with the `.hex` in `hex/` (ModusToolbox / IDE programmer).
4. **Start Bitstream Studio** — open the Bitstream panel; ensure the bridge is running (status bar / backend services on extension activate).
5. **Serve web examples** — Command Palette → **Serve Web App Folder over HTTP** → select the cloned **`web-app`** folder → open `index.html` from the served URL.
6. **Connect telemetry** — toolbar **Bitstream** + COM port, or **Simulator** with the external bitstream-simulator extension.

Web pages read live samples from the Bitstream Telemetry Provider (`ws://127.0.0.1:9997`) via the shipped `/sdk/live-data.js` bundle.

## Web examples

| File | Description |
|------|-------------|
| `ex01_sht40.html` | Reference: SHT40 temp + humidity |
| `ex02_dps368.html` | DPS368 pressure + temperature |
| `ex03_bmm350.html` | BMM350 magnetometer + compass |
| `ex04_bmi270_imu.html` | BMI270 accel + gyro |
| `ex05_bmi270_orientation.html` | BMI270 artificial horizon |
| `ex06_dashboard.html` | All four sensors (compact) |
| `ex07_catalog_browser.html` | `SENSOR_CATALOG` browser |
| `ex08_stale_and_route.html` | Stale + route/origin log |

`ex01` is self-contained. `ex02`–`ex08` use `web-app/shared/`.

## Maintainer — refresh drops

| Artifact | Source | Drop location |
|----------|--------|---------------|
| VSIX | `npm run compile && npm run package` in Bitstream-Studio `extension/` | `vsix/bitstream-studio-<version>.vsix` |
| HEX | TESAIoT firmware `app_combined.hex` | `hex/tesaiot-bitstream-<version>.hex` |

See `vsix/README.md` and `hex/README.md` for naming notes.

## Offline SDK fallback

If not using **Serve Web App Folder over HTTP**, copy `live-data.browser.js` from Bitstream-Studio `packages/live-data/dist/` to `web-app/vendor/live-data.js` and serve `web-app/` with any static server (`npx serve web-app`).
