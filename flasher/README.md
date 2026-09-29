# TESAIoT Flasher — user guide

Desktop app to **flash firmware** onto the **TESAIoT PSoC Edge DevKit** over USB (KitProg3). Use it with the `.hex` files in [`../hex/`](../hex/) and the Bitstream Studio extension from [`../vsix/`](../vsix/).

**Product line:** new builds ship as **Tauri** (`com.tesaiot.flasher`) from Bitstream-Studio tags `tesaiot-flasher-v*`. The **0.1.6** installers below are the last **Electron** drop (still usable until a Tauri Windows `.exe` is copied into this folder).

## What you need

| Item | Notes |
|------|--------|
| **Board** | TESAIoT PSoC Edge DevKit + USB cable (KitProg3) |
| **Firmware** | A `.hex` from [`../hex/`](../hex/) — match the VSIX version when you can |
| **This installer** | Windows preferred for the Tauri line; table below for current drops |

## Pick the right installer

| File | Use on | Notes |
|------|--------|--------|
| *(Tauri)* `TESAIoT Flasher_*_x64-setup.exe` | **Windows** 10/11 (64-bit) | From GitHub Release `tesaiot-flasher-v*` when published here |
| `TESAIoT.Flasher.Setup.0.1.6.exe` | **Windows** 10/11 (64-bit) | Legacy Electron |
| `TESAIoT.Flasher-0.1.6-arm64.dmg` | **macOS** Apple Silicon | Legacy Electron — last macOS ship |
| `TESAIoT.Flasher-0.1.6.dmg` | **macOS** Intel | Legacy Electron |
| `TESAIoT.Flasher-0.1.6.AppImage` | **Linux** 64-bit | Legacy Electron |
| `tesaiot-flasher_0.1.6_amd64.deb` | **Linux** 64-bit (Debian/Ubuntu) | Legacy Electron |

## Install (Windows)

1. Run the Windows `.exe` installer (Tauri when available, else **0.1.6** Setup).
2. Launch **TESAIoT Flasher**.
3. First launch stages OpenOCD + tools locally — no separate Node / ModusToolbox install.
4. If KitProg3 is missing, install the bundled driver (legacy app: **Install Driver**), then replug USB.

### macOS / Linux (legacy 0.1.6 only)

Use the DMG / AppImage / `.deb` from the table. New Tauri releases are **Windows-first**.

## Flash firmware

1. Connect the DevKit over USB.
2. Open **TESAIoT Flasher**.
3. **Firmware source:** GitHub catalog (`tesaiot-bitstream-…`) or a local `.hex` from [`../hex/`](../hex/).
4. Click **Flash** and wait for success (or follow on-screen fail tips).
5. Unplug/replug USB if the COM port does not appear in Bitstream Studio.

Catalog JSON may include a **memory** footprint for the build map panel — see [`../hex/firmware-manifest.json`](../hex/firmware-manifest.json).

## After flashing

1. Install **Bitstream Studio** from [`../vsix/`](../vsix/) (same version as the firmware when possible).
2. Toolbar: **Bitstream** (not Simulator).
3. Open the **COM** port at **921600**.

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| **No device / no COM port** | Replug USB; another cable/port; Windows → install KitProg driver |
| **Flash fails** | Follow the fail banner tips; close other OpenOCD tools; retry after replug |
| **macOS “unidentified developer”** | Right-click app → **Open** (legacy 0.1.6) |
| **Connected but no data in Studio** | Toolbar **Bitstream**; baud **921600**; firmware and VSIX versions match |

More: [`../hex/README.md`](../hex/README.md) · [`../vsix/README.md`](../vsix/README.md)
