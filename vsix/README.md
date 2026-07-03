# Bitstream Studio VSIX (latest build)

Drop the **most recent** Bitstream Studio extension `.vsix` here for hackathon handoff.

Replace the previous file when you package a new build — keep **one** canonical VSIX in this folder.

## Build (from Bitstream-Studio)

```bash
cd extension
npm run compile
npm run package
```

Copy the generated VSIX into this folder:

```bash
cp extension/bitstream-studio-*.vsix vsix/
```

(from the Bitstream-Studio repo root after clone)

## Install

VS Code → Extensions → `…` → **Install from VSIX…** → select the file in this folder.

Optionally add `BUILD.txt` with version, git commit, and build date when you refresh the VSIX.
