# Bitstream Studio VSIX — user guide

Packaged **Bitstream Studio** extension builds for hackathon handoff. Install one of these **`.vsix`** files in **VS Code** or **Cursor** to get the Sensor Telemetry, Sensor Studio, and Bitstream tooling without cloning or building the repo.

## What you need

| Item | Notes |
|------|--------|
| **Editor** | [VS Code](https://code.visualstudio.com/) or [Cursor](https://cursor.com/) |
| **Matching firmware** (hardware labs) | Flash the same version from [`../hex/`](../hex/) — e.g. `bitstream-studio-0.1.5.vsix` + `tesaiot-bitstream-0.1.5.hex` |
| **DevKit** (optional) | TESAIoT PSoC Edge + USB for **Bitstream** (UART) mode |

You can explore much of the UI in **Simulator** mode without a board (separate Bitstream Simulator extension + local bridge). For real sensor data, use **Bitstream** mode with flashed firmware.

## Pick a version

1. Download **`bitstream-studio-<version>.vsix`** from this folder (highest version number is usually newest).
2. **Match the firmware** when using hardware: same `<version>` as the `.hex` in [`../hex/`](../hex/). See [`../hex/firmware-manifest.json`](../hex/firmware-manifest.json) for firmware release notes.
3. If your instructor gave you a specific version, use that file — do not mix a newer VSIX with older firmware (or the reverse).

## Install the extension

### VS Code

1. Open **VS Code**.
2. Go to **Extensions** (sidebar or `Ctrl+Shift+X` / `Cmd+Shift+X`).
3. Click the **`…`** menu at the top of the Extensions view.
4. Choose **Install from VSIX…**
5. Select the downloaded **`bitstream-studio-<version>.vsix`**.
6. When prompted, **Reload** the window (or run **Developer: Reload Window** from the Command Palette).

### Cursor

Same steps as VS Code: **Extensions** → **`…`** → **Install from VSIX…** → reload.

### Command line (optional)

If `code` or `cursor` is on your PATH:

```bash
code --install-extension bitstream-studio-0.1.5.vsix
# or
cursor --install-extension bitstream-studio-0.1.5.vsix
```

Replace the filename with your chosen version.

## Open Bitstream Studio

After reload:

1. Open the **Command Palette** (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **Open Bitstream Studio** (or **Open Bitstream Studio (Sensor Studio tab)** / **Sensor Telemetry tab**).

The app opens in an editor panel. Backend services (WebSocket broker, telemetry provider) start with the extension — you do not need a separate `npm start` when using the installed VSIX.

## First run checklist

| Step | Action |
|------|--------|
| **1. Free 3D assets** | Command Palette → **Download Free Assets from GitHub** (or **Open Free Assets Loader**) — models are not bundled in the VSIX |
| **2. Flash firmware** | Follow [`../hex/README.md`](../hex/README.md) if you have a DevKit |
| **3. Connect UART** | Toolbar → **Bitstream** (not Simulator) → select **COM** port → **921600** baud |
| **4. Confirm data** | Sensor Telemetry or Sensor Studio should show live samples after HELLO/handshake |

## Telemetry modes

| Mode | When to use |
|------|-------------|
| **Bitstream** | Real DevKit over USB serial — requires matching firmware from [`../hex/`](../hex/) |
| **Simulator** | No hardware — install the separate **Bitstream Simulator** extension and switch the toolbar to **Simulator** |

Only one mode is active at a time; switching clears mixed telemetry.

## Files in this folder

| File | Purpose |
|------|---------|
| `bitstream-studio-<version>.vsix` | Installable extension for that release |

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| **Install blocked / “unsupported”** | Use VS Code **1.85+** or current Cursor; download the VSIX again (corrupt download) |
| **Extension missing after reload** | Extensions view → confirm **Bitstream Studio** is enabled; reinstall from VSIX |
| **Blank or stale panel** | Command Palette → **Bitstream Studio: Reload Webview** or **Reload Window** |
| **No COM port / no data** | Flash firmware from [`../hex/`](../hex/); toolbar **Bitstream**; baud **921600**; replug USB |
| **UI errors / protocol mismatch** | Align VSIX and firmware versions; install the pair from the same hackathon drop |
| **3D models missing** | Run **Download Free Assets from GitHub** once per machine |

