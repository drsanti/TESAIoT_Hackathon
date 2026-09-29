# Bitstream Studio — desktop installers

Standalone **Bitstream Studio** (Tauri) for participants who prefer an app instead of the VS Code VSIX.

Pair with firmware from [`../hex/`](../hex/) (same **0.5.0** line when possible).

## Pick the right installer

| File | Use on |
|------|--------|
| `Bitstream.Studio_0.5.0_x64-setup.exe` | **Windows** 10/11 (64-bit) — NSIS installer |
| `Bitstream.Studio_0.5.0_aarch64.dmg` | **macOS** Apple Silicon (M1/M2/M3/…) |
| *(Linux)* | **Not shipped** — current Tauri desktop pipeline builds Windows + macOS only. On Linux use the [VSIX](../vsix/) in VS Code / Bitstream IDE. |

## Install

### Windows

1. Run **`Bitstream.Studio_0.5.0_x64-setup.exe`**.
2. Launch **Bitstream Studio** from the Start menu.
3. Prefer **Quit** from the tray icon before reinstalling or running a debug `desktop:dev` build.

### macOS

1. Open the **`.dmg`**.
2. Drag **Bitstream Studio** into **Applications**.

Unsigned internal builds may need **Right-click → Open** the first time.

## Notes

- App id: `dev.ternion.bitstream-studio`
- Desktop product version tracks the installer filename (**0.5.0**).
- Webview workspaces in this build use the **desktop** release profile (Sensor Studio + Telemetry + Twin Factory + Block Studio). **Neuron Studio** is in the extension `v0.5.x` line — prefer the VSIX for Neuron until a desktop profile includes it.
- Spec: Bitstream-Studio `extension/docs/DESKTOP_PACKAGING.md`
