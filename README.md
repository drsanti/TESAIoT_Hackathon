# TESAIoT Hackathon

Use this repo to install **Bitstream Studio**, flash your **TESAIoT PSoC Edge DevKit**, and try **live sensor web demos** — no firmware or extension build required.

**Repository:** [github.com/drsanti/TESAIoT_Hackathon](https://github.com/drsanti/TESAIoT_Hackathon)

---

## What is in this repo?

| Folder | What it is for |
|--------|----------------|
| [`vsix/`](vsix/) | Bitstream Studio extension — install in VS Code or Cursor |
| [`hex/`](hex/) | DevKit firmware — flash before hardware labs |
| [`flasher/`](flasher/) | TESAIoT Flasher desktop installers (Windows / macOS) |
| [`web-app/`](web-app/) | Sample HTML pages that show live sensor readings |

**Tip:** Use the **same version number** for the VSIX and firmware when you can (for example `0.1.5` for both). Check [`hex/firmware-manifest.json`](hex/firmware-manifest.json) for available firmware builds and notes.

---

## What you need

| Item | When you need it |
|------|------------------|
| [VS Code](https://code.visualstudio.com/) or [Cursor](https://cursor.com/) | Always — to run Bitstream Studio |
| **TESAIoT PSoC Edge DevKit** + USB cable | Hardware labs (**Bitstream** mode) |
| **TESAIoT Flasher** or **ModusToolbox** | To flash firmware from [`hex/`](hex/) — installers in [`flasher/`](flasher/) |
| **Bitstream Simulator** extension (optional) | Try the UI **without** a board (**Simulator** mode) |

---

## Quick start

### 1. Download this repo

**Option A — Git:**

```bash
git clone https://github.com/drsanti/TESAIoT_Hackathon.git
cd TESAIoT_Hackathon
```

**Option B — ZIP:** On GitHub, click **Code → Download ZIP**, then extract the folder.

### 2. Install Bitstream Studio

1. Open the [`vsix/`](vsix/) folder and note the newest **`bitstream-studio-<version>.vsix`** (or use the version your instructor gave you).
2. In VS Code or Cursor: **Extensions** → **`…`** → **Install from VSIX…** → select that file.
3. Click **Reload** when prompted.
4. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) → **Open Bitstream Studio**.

More detail: [`vsix/README.md`](vsix/README.md)

**Optional — install from the terminal** (from the repo folder; change the version if needed):

```bash
code --install-extension vsix/bitstream-studio-0.1.5.vsix
code -r
```

Use `cursor` instead of `code` if you use Cursor. To replace an older install first:

```bash
code --uninstall-extension TERNIONDEV.bitstream-studio
```

### 3. Flash firmware (hardware labs)

1. Open [`hex/`](hex/) and pick **`tesaiot-bitstream-<version>.hex`** with the **same version** as your VSIX.
2. Flash the board with **TESAIoT Flasher** ([`flasher/`](flasher/)) or **ModusToolbox**.
3. If no serial port appears, unplug and replug the USB cable.

More detail: [`hex/README.md`](hex/README.md)

### 4. Connect your board or simulator

1. In Bitstream Studio, choose **Bitstream** (real DevKit) or **Simulator** (no hardware).
2. For **Bitstream**: select your **COM** port and set baud rate to **921600**.
3. Open **Sensor Telemetry** or **Sensor Studio** and confirm readings update.

Bitstream Studio starts its background services when the extension loads — nothing else to install for normal use.

### 5. First-time tips

| Goal | What to do |
|------|------------|
| **3D models in the UI** | Command Palette → **Download Free Assets from GitHub** |
| **Blank or frozen panel** | Command Palette → **Bitstream Studio: Reload Webview**, or **Developer: Reload Window** |

---

## Web app examples

The [`web-app/`](web-app/) folder has simple HTML pages that display **live sensor data** while Bitstream Studio is running on your computer.

### How to run

1. Complete steps 2 and 4 above (extension installed, telemetry connected).
2. Command Palette → **Serve Web App Folder over HTTP** → select the **`web-app`** folder from this repo.
3. Click the link in the notification, or open **`index.html`** from that served URL.
4. Choose an example from the list.

Open [`web-app/index.html`](web-app/index.html) in the served site for a full catalog and short instructions.

### Examples

| Page | Sensors / topic |
|------|-----------------|
| [ex01 — SHT40](web-app/ex01_sht40.html) | Temperature and humidity |
| [ex02 — DPS368](web-app/ex02_dps368.html) | Pressure and temperature |
| [ex03 — BMM350](web-app/ex03_bmm350.html) | Magnetometer and compass |
| [ex04 — BMI270 IMU](web-app/ex04_bmi270_imu.html) | Accelerometer and gyro |
| [ex05 — BMI270 horizon](web-app/ex05_bmi270_orientation.html) | Artificial horizon |
| [ex06 — Dashboard](web-app/ex06_dashboard.html) | All four sensors |
| [ex07 — Catalog browser](web-app/ex07_catalog_browser.html) | Browse sensor catalog |
| [ex08 — Stale / route](web-app/ex08_stale_and_route.html) | Connection status demo |

---

## Bitstream vs Simulator

| Mode | Use this when |
|------|----------------|
| **Bitstream** | Your DevKit is plugged in and firmware from [`hex/`](hex/) is flashed |
| **Simulator** | You have no board — install the separate **Bitstream Simulator** extension |

Use one mode at a time. Switching modes clears old sample data.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| **VSIX will not install** | Use VS Code 1.85+ or a current Cursor build; download the VSIX again |
| **Bitstream panel is blank** | Reload the webview or reload the window; check the extension is enabled |
| **No COM port** | Re-flash firmware; try another USB port or cable; on Windows, install the KitProg3 driver |
| **Port open but no sensor data** | Toolbar set to **Bitstream**; baud **921600**; VSIX and firmware versions match |
| **Web examples show no data** | Bitstream Studio is open; board or simulator connected; you used **Serve Web App Folder over HTTP** on the `web-app` folder |
| **Missing 3D models** | Command Palette → **Download Free Assets from GitHub** |

Step-by-step help: [`vsix/README.md`](vsix/README.md) · [`hex/README.md`](hex/README.md)
