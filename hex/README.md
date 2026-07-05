# Firmware for TESAIoT / Bitstream — user guide

Prebuilt **`.hex`** images for the **TESAIoT PSoC Edge DevKit**. Each file is paired with a **Bitstream Studio** extension version so hackathon participants can flash the board and run the same host UI without building firmware from source.

## What you need

| Item | Notes |
|------|--------|
| **Board** | TESAIoT PSoC Edge DevKit, connected over **KitProg3** USB |
| **Bitstream Studio** | Install the matching **`.vsix`** from [`../vsix/`](../vsix/) (same version number as the firmware when possible) |
| **Flash tool** | **TESAIoT Flasher** (easiest) or Infineon **ModusToolbox** |

## Pick a firmware version

1. Open **`firmware-manifest.json`** in this folder — it lists every published build, size, date, and short release notes.
2. Choose the file **`tesaiot-bitstream-<version>.hex`** (for example `tesaiot-bitstream-0.1.5.hex`).
3. **Match the VSIX** when you can: firmware `0.1.5` + `bitstream-studio-0.1.5.vsix` avoids protocol/UI mismatches.

If you only need “what’s newest,” use the **`latest`** field in `firmware-manifest.json`.

## Flash the board

### Option A — TESAIoT Flasher (recommended)

The desktop flasher can download firmware directly from this GitHub folder.

1. Install **TESAIoT Flasher** from [`../flasher/`](../flasher/) (see [`flasher/README.md`](../flasher/README.md)).
2. Connect the DevKit over USB; click **Refresh** if the port does not appear.
3. In the firmware picker, choose a **GitHub catalog** entry (`tesaiot-bitstream-…`) **or** switch to **Local file** and select the `.hex` you downloaded from this repo.
4. Run **Flash** and wait until the tool reports success.
5. Unplug/replug USB once if the serial port does not show up.

On **Windows**, use **Install Driver** in the flasher UI if KitProg3 is not detected.

### Option B — ModusToolbox

1. Install [ModusToolbox](https://softwaretools.infineon.com).
2. Open the **Program** (or **Device Programmer**) flow for your kit.
3. Select the downloaded **`tesaiot-bitstream-<version>.hex`** as the image to program.
4. Program and verify.

## After flashing

1. Install **Bitstream Studio** from VS Code: Extensions → `…` → **Install from VSIX…** → pick the matching file under [`../vsix/`](../vsix/).
2. Reload the VS Code window.
3. Start the dev stack (or use a packaged workflow your instructor provides). Typical local dev:
   ```bash
   cd extension
   npm install
   npm start
   ```
4. In Bitstream Studio, set the toolbar to **Bitstream** (UART), open the **COM** port at **921600**, and confirm sensor telemetry appears.

For **Simulator** mode you do not need this firmware — use the separate Bitstream Simulator extension instead.

## Files in this folder

| File | Purpose |
|------|---------|
| `tesaiot-bitstream-<version>.hex` | Flash image for that Bitstream Studio release |
| `firmware-manifest.json` | Version list, sizes, dates, and notes for the flasher catalog |

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| **No COM port** | Replug USB; confirm KitProg3 in Device Manager (Windows) or `ioreg` (macOS); re-flash |
| **Flash fails** | Different USB cable/port; run flasher as admin on Windows; install KitProg3 driver |
| **Connected but no data** | Toolbar must be **Bitstream** (not Simulator); baud **921600**; reload VS Code after VSIX install |
| **UI looks wrong / errors** | Align firmware and VSIX versions; pull the latest pair from this repo |

