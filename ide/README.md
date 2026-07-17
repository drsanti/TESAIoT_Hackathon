# BitStream IDE — user installers

Desktop **BitStream IDE** installers (Code-OSS fork with Bitstream Studio built in). Use these when you want a single app instead of installing VS Code/Cursor + a VSIX.

Source releases: [github.com/drsanti/bitstream-ide-private](https://github.com/drsanti/bitstream-ide-private/releases) (private maintainer repo). Participant copies live in this folder after a handoff refresh.

Releases ship the **slim** installer only. Free 3D assets are downloaded inside Bitstream Studio after install (not bundled in the `.exe`).

## Pick the right installer

| File pattern | Use on |
|--------------|--------|
| `BitStreamIDEUserSetup-x64-*.exe` | **Windows** 10/11 — per-user slim installer |
| `BitStreamIDE*Slim*.dmg` | **macOS** (when published) |
| `*.deb` / `*.rpm` | **Linux** (when published) |

See `BUILD.txt` in this folder for the exact version and file list currently dropped here (local maintainer metadata; may be gitignored).

## Install (Windows)

1. Download `BitStreamIDEUserSetup-x64-*.exe` from this folder.
2. Run the installer (per-user; no admin required for UserSetup).
3. Launch **BitStream IDE** from the Start menu.
4. Open **Bitstream Studio** from the activity bar or Command Palette.
5. When prompted, **download the free 3D asset pack** (Free Assets Loader). Stay online until the download finishes. You can dismiss and open Free Loader later from the Bitstream Studio menu if needed.

If the app exits immediately after install, reinstall from a **fresh** release build (older packages had a corrupt ASAR issue that is fixed in current packaging).

## After install

1. Prefer matching **firmware** from [`../hex/`](../hex/) when using the DevKit.
2. Optional: install **TESAIoT Flasher** from [`../flasher/`](../flasher/) to flash HEX.
3. Free 3D assets: use Free Assets Loader when prompted (or Setup / Command Palette → download TERNION assets).

## Maintainer refresh

From the BitStream IDE repo:

```bash
node ternion/download-ide-release-to-hackathon.mjs --tag bitstream-ide-v0.1.10
```

Then commit/push **TESAIoT_Hackathon** (use Git LFS for large `.exe` / `.dmg` if configured). The download script keeps slim installers only (drops any legacy `*Assets*` artifacts).

Related: Bitstream Studio VSIX-only path remains [`../vsix/`](../vsix/).
