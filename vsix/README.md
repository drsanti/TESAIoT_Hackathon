# Bitstream Studio VSIX (versioned build)

Drop the Bitstream Studio extension `.vsix` here for hackathon handoff.

Filename: **`bitstream-studio-<version>.vsix`** where `<version>` matches `extension/package.json` (e.g. `bitstream-studio-0.1.4.vsix`).

## Refresh

```bash
cd extension && npm run compile && npm run package
bash .cursor/skills/tesaiot-hackathon-hex-drop/scripts/copy-hackathon-vsix.sh
```

Or HEX + VSIX together: `copy-hackathon-handoff.sh`. Metadata: `BUILD.txt`.

## Install

VS Code → Extensions → `…` → **Install from VSIX…** → select **`bitstream-studio-<version>.vsix`** in this folder.
