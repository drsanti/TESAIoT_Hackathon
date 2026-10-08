# Bitstream Studio VSIX — user guide

Packaged **Bitstream Studio** extension builds for hackathon handoff. Install a **`.vsix`** from this folder in any **VS Code–compatible IDE** to get Sensor Telemetry, Sensor Studio, Neuron, Twin Factory (tier-dependent), UART bridge, and related tooling — without cloning or building the monorepo.

**Latest full build (recommended):** [`bitstream-studio-0.5.2.vsix`](./bitstream-studio-0.5.2.vsix)

> **Marketplace note:** The Visual Studio Marketplace listing for Bitstream Studio may point here for the **full** sideload build (native serial + complete webview). Prefer the newest `.vsix` in this folder for workshops and DevKit labs.

## What you need

| Item | Notes |
|------|--------|
| **Editor** | Any **VS Code–compatible IDE** — [Visual Studio Code](https://code.visualstudio.com/), [Cursor](https://cursor.com/), VSCodium, Windsurf, Trae, and other Code OSS–based editors |
| **Matching firmware** (hardware labs) | Flash the same version from [`../hex/`](../hex/) — e.g. `bitstream-studio-0.5.2.vsix` + matching `tesaiot-bitstream-*.hex` (see [`../hex/firmware-manifest.json`](../hex/firmware-manifest.json)) |
| **DevKit** (optional) | TESAIoT PSoC Edge + USB for **Bitstream** (UART) mode |

You can explore much of the UI in **Simulator** mode without a board (separate Bitstream Simulator extension + local bridge). For real sensor data, use **Bitstream** mode with flashed firmware.

## Git LFS (clones only)

`.vsix` files in this repo are stored with **[Git LFS](https://git-lfs.com/)** (see [`.gitattributes`](../.gitattributes)).

| How you get the file | What to do |
|----------------------|------------|
| **Download from GitHub in the browser** | Use the file page → **Download** (GitHub serves the real binary) |
| **`git clone` / `git pull`** | Install Git LFS, then `git lfs install` and `git lfs pull` — otherwise you may get tiny pointer files instead of the VSIX |

## Pick a version

1. Download **`bitstream-studio-<version>.vsix`** from this folder (highest version number is usually newest — currently **0.5.2**).
2. **Match the firmware** when using hardware: same release line as the `.hex` in [`../hex/`](../hex/). See [`../hex/firmware-manifest.json`](../hex/firmware-manifest.json) for firmware release notes.
3. If your instructor gave you a specific version, use that file — do not mix a newer VSIX with older firmware (or the reverse).

## Install the extension

### VS Code–compatible IDEs (VS Code, Cursor, VSCodium, …)

1. Open your editor.
2. Go to **Extensions** (sidebar or `Ctrl+Shift+X` / `Cmd+Shift+X`).
3. Click the **`…`** menu at the top of the Extensions view.
4. Choose **Install from VSIX…**
5. Select the downloaded **`bitstream-studio-<version>.vsix`**.
6. When prompted, **Reload** the window (or run **Developer: Reload Window** from the Command Palette).

### Command line (optional)

If your editor CLI is on `PATH` (`code`, `cursor`, `codium`, …):

```bash
code --install-extension bitstream-studio-0.5.2.vsix
# or
cursor --install-extension bitstream-studio-0.5.2.vsix
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
| `bitstream-studio-<version>.vsix` | Installable full extension for that release (LFS) |
| `README.md` | This guide |

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| **VSIX is only a few hundred bytes** | Git LFS pointer — run `git lfs pull`, or download the file from the GitHub website |
| **Install blocked / “unsupported”** | Use a current VS Code–compatible IDE (engines **^1.75**); re-download the VSIX |
| **Extension missing after reload** | Extensions view → confirm **Bitstream Studio** is enabled; reinstall from VSIX |
| **Blank or stale panel** | Command Palette → **Bitstream Studio: Reload Webview** or **Reload Window** |
| **No COM port / no data** | Flash firmware from [`../hex/`](../hex/); toolbar **Bitstream**; baud **921600**; replug USB |
| **UI errors / protocol mismatch** | Align VSIX and firmware versions; install the pair from the same hackathon drop |
| **3D models missing** | Run **Download Free Assets from GitHub** once per machine |
