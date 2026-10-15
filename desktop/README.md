# Bitstream Studio — desktop installers

Standalone **Bitstream Studio** (Tauri) for participants who prefer an app instead of the VS Code VSIX.

**v0.7.0** ships a **Rust** Bitstream Backend sidecar (no Node.js). Pair with thin Marketplace VSIX **0.7.0** or Hackathon VSIX, plus firmware from [`../hex/`](../hex/).

## Pick the right installer

| File | Use on |
|------|--------|
| `Bitstream.Studio_0.7.0_x64-setup.exe` | **Windows** 10/11 (64-bit) — NSIS installer |
| `Bitstream.Studio_0.7.0_aarch64.dmg` | **macOS** Apple Silicon (when CI uploads) |
| *(Linux)* | Prefer [Backend zip](../backend/) + [VSIX](../vsix/); AppImage is best-effort on GitHub Releases |

GitHub Release: [bitstream-desktop-v0.7.0](https://github.com/drsanti/Bitstream-Studio/releases/tag/bitstream-desktop-v0.7.0)

Prior **0.5.0** (Node sidecar) installers may remain in this folder as archive — prefer **0.7.0**.

## Install

### Windows

1. Run **`Bitstream.Studio_0.7.0_x64-setup.exe`**.
2. Launch **Bitstream Studio** from the Start menu.
3. Prefer **Quit** from the tray icon before reinstalling or running a debug `desktop:dev` build.

### macOS

1. Open the **`.dmg`**.
2. Drag **Bitstream Studio** into **Applications**.

Unsigned internal builds may need **Right-click → Open** the first time.

## Notes

- App id: `dev.ternion.bitstream-studio`
- Desktop product version tracks the installer filename (**0.7.0**).
- Sidecar: Rust `bitstream-backend` only (ADR-019). MQTT not embedded — attach to a foreign broker if needed.
- Spec: Bitstream-Studio `extension/docs/DESKTOP_PACKAGING.md`
