# TESAIoT Flasher — user guide

Desktop app to **flash firmware** onto the **TESAIoT PSoC Edge DevKit** over USB (KitProg3). Use it with the `.hex` files in [`../hex/`](../hex/) and the Bitstream Studio extension from [`../vsix/`](../vsix/).

## What you need

| Item | Notes |
|------|--------|
| **Board** | TESAIoT PSoC Edge DevKit + USB cable (KitProg3) |
| **Firmware** | A `.hex` from [`../hex/`](../hex/) — match the VSIX version when you can |
| **This installer** | One file below for your computer’s OS |

## Pick the right installer

| File | Use on |
|------|--------|
| `TESAIoT.Flasher.Setup.0.1.5.exe` | **Windows** 10/11 (64-bit) |
| `TESAIoT.Flasher-0.1.5-arm64.dmg` | **macOS** on Apple Silicon (M1/M2/M3) |
| `TESAIoT.Flasher-0.1.5.dmg` | **macOS** on Intel Macs |

**Not sure which Mac file?** Try the **arm64** DMG first on Apple Silicon. On Intel Macs, use the other DMG.

**Linux** (`.AppImage` / `.deb`) may be added in a later handoff drop — ask your instructor or check this folder again.

## Install

### Windows

1. Double-click **`TESAIoT.Flasher.Setup.0.1.5.exe`**.
2. Follow the setup wizard (you can change the install folder).
3. Launch **TESAIoT Flasher** from the Start menu or desktop shortcut.

If KitProg3 is not detected, open the app and use **Install Driver**, then replug USB.

### macOS

1. Open the **`.dmg`** for your Mac type.
2. Drag **TESAIoT Flasher** into **Applications**.
3. First launch: if macOS blocks the app, **right-click** the app → **Open** → **Open** (needed for unsigned builds).

## Flash firmware

1. Connect the DevKit over USB.
2. Open **TESAIoT Flasher** and click **Refresh** if the board is not listed.
3. **Firmware source**
   - **GitHub releases** (default): pick a `tesaiot-bitstream-…` build from the catalog (same repo as [`../hex/`](../hex/)), **or**
   - **Local file**: choose a `.hex` you downloaded from [`../hex/`](../hex/).
4. Click **Flash** and wait for **Flash successful** in the log.
5. Unplug and replug USB if the serial port does not appear in Bitstream Studio.

Pair firmware with the matching VSIX — see [`../hex/firmware-manifest.json`](../hex/firmware-manifest.json) and [`../vsix/`](../vsix/).

## After flashing

1. Install **Bitstream Studio** from [`../vsix/`](../vsix/) (same version as the firmware when possible).
2. In the toolbar, choose **Bitstream** (not Simulator).
3. Open the **COM** port at **921600** and confirm sensor data in Sensor Telemetry or Sensor Studio.

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| **No device / no COM port** | Replug USB; another cable or port; **Refresh** in the flasher; Windows → **Install Driver** |
| **Flash fails** | Pick the correct `.hex`; close other tools using the port; retry after replug |
| **macOS “unidentified developer”** | Right-click app → **Open** (see Install above) |
| **Connected but no data in Bitstream Studio** | Toolbar **Bitstream**; baud **921600**; firmware and VSIX versions match |

More firmware help: [`../hex/README.md`](../hex/README.md) · Extension install: [`../vsix/README.md`](../vsix/README.md)
