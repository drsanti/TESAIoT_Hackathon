# ble-react — Ternion BitStream BLE client (React)

Publishable **React + TypeScript** monorepo for talking to **TESAIoT firmware over BLE**. Labs use **Web Bluetooth** or a **Node host BLE bridge** (recommended on Windows when Chromium WinRT drops GATT).

**Status:** Interactive tutorial + packages implemented (EVT-first). npm publish is prep-only.

---

## Documentation (read in order)

| Doc | Purpose |
|-----|---------|
| [docs/LABS.md](./docs/LABS.md) | Tutorial map, run commands, EVT-first notes, RESET tip |
| [docs/WEB_BLUETOOTH_WINDOWS.md](./docs/WEB_BLUETOOTH_WINDOWS.md) | Windows Web Bluetooth + **Node bridge** bring-up |
| [tools/ble-bridge/README.md](./tools/ble-bridge/README.md) | Host BLE → WebSocket bridge |
| [docs/REQUIREMENTS.md](./docs/REQUIREMENTS.md) | Functional / non-functional requirements |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Layers, packages, naming |
| [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) | Phased build order (updated for EVT-first smoke) |
| [docs/ADDONS.md](./docs/ADDONS.md) | Extension API v1 (addon-kit deferred after labs) |

---

## What this repo is

| Sibling in hackathon | Role |
|----------------------|------|
| [`../web-app/`](../web-app/) | HTML demos via Bitstream Studio telemetry (WS / MQTT) — **no direct BLE** |
| [`../python-app/`](../python-app/README.md) | Python EVT-first teaching labs (bleak) |
| [`../ble-flet/`](../ble-flet/) | Desktop BLE dashboard (Python Flet + bleak) |
| **`ble-react/`** | Browser tutorial → dashboard + **`@ternion/tbs-*`** (+ optional Node bridge) |

---

## Quick start

```bash
cd TESAIoT_Hackathon/ble-react
pnpm install
pnpm test

# Terminal 1 — Node BLE bridge (Windows recommended)
pnpm bridge:install && pnpm bridge

# Terminal 2 — labs UI
pnpm dev              # http://localhost:5174/?ble=bridge
pnpm dev:dashboard    # http://localhost:5175/
```

Open in **system Chrome or Edge** (not Cursor’s embedded browser). Follow the learning path → Why / Do / Check on each chapter.

**Windows:** if Chapter 03+ fails right after connect, pair the board in **Windows Settings → Bluetooth** first, then use `http://localhost:5174/diag` (**Run all 1→6**). Details: [docs/WEB_BLUETOOTH_WINDOWS.md](./docs/WEB_BLUETOOTH_WINDOWS.md). Verified 2026-07-18: after OS pair, `/diag` all green.

---

## Layout

```text
packages/tbs-core          wire / chunk / decode
packages/tbs-ble-session   goLive + CFG fire-and-forget
apps/labs                  interactive tutorial (shared Web Bluetooth session)
apps/labs/src/tutorial     TutorialShell / steps / progress
apps/dashboard             Connect / Live / Link / Log
```

---

## Firmware prerequisites

1. Flash HEX from [`../hex/`](../hex/).
2. One-time: enable **BLE module profile** bit `0x08` in Bitstream Studio → reboot (UART step). Runtime does **not** need Studio.
3. Disconnect other BLE centrals.
4. After connect timeout, press **RESET** until TFT soft-blue.

---

## Teaching path (EVT-first)

Canonical flow matches python-app:

1. Connect GATT  
2. `startNotifications` on BS_TX (CCCD arms `TX_EVT`)  
3. Decode `EVT_SENSOR`  

PING / POLICY wait is **advanced / optional**, not early-lab acceptance.

---

## Reference code to port (do not import at runtime)

| Source | Use for |
|--------|---------|
| [`../python-app/shared/`](../python-app/shared/) | SessionLite / wire / decode parity |
| Bitstream Studio `packages/bitstream-ble-client` | GATT UUIDs, chunk envelope v1 |

**Rule:** `ble-react` must **not** depend on `Bitstream-Studio/extension/` at build time.

---

## License

TBD — align with TESAIoT Hackathon / Ternion policy when publishing `@ternion/*` packages.
