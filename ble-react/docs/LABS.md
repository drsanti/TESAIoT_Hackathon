# ble-react teaching labs (Web Bluetooth tutorial)

Interactive React curriculum under `apps/labs`. Each chapter is a guided **Why → Do → Check** lesson.

Teaching path (EVT-first):

**connect → startNotifications(BS_TX) → decode EVT_SENSOR**

Do **not** gate early labs on PING / POLICY RES. Current firmware arms `TX_EVT` when CCCD enables notify.

v1 labs speak BS2 over BLE. On Windows, prefer the **Node host bridge** when browser Web Bluetooth drops after connect.

---

## Run

```bash
cd TESAIoT_Hackathon/ble-react
pnpm install
pnpm test

# Terminal A — host BLE (recommended on Windows)
pnpm bridge:install && pnpm bridge

# Terminal B — UI
pnpm dev          # tutorial → http://localhost:5174/?ble=bridge
pnpm dev:dashboard  # polished app → http://localhost:5175/
```

Use **system Chrome or Edge** for the UI. Soft context: `http://localhost`. Connect bar → **Host bridge (Node)** (default on Windows).

Web Bluetooth-only: `?ble=web` (often fails on WinRT — see [WEB_BLUETOOTH_WINDOWS.md](./WEB_BLUETOOTH_WINDOWS.md)).

---

## Prerequisites (every chapter)

1. Flash HEX from [`../hex/`](../hex/); TFT **soft-blue** advertising `TESAIoT-*`.
2. One BLE central only (disconnect nRF Connect / python-app / other browsers).
3. After a failed connect, press board **RESET** if advertising vanishes.
4. **Windows (required when Chapter 03+ drops):** pair `TESAIoT-*` in **Settings → Bluetooth** before Connect. Then hard-reload and connect once.

Sibling [`../web-app/`](../web-app/) is **WS/MQTT via Studio** — not direct BLE.

---

## Troubleshooting (Windows Web Bluetooth)

Canonical notes: **[WEB_BLUETOOTH_WINDOWS.md](./WEB_BLUETOOTH_WINDOWS.md)**.

| Check | URL / command |
|-------|----------------|
| Fresh browser steps (no lab session) | `http://localhost:5174/diag` → **Run all 1→6** |
| Host firmware proof (bleak) | `python-app/tools/ble_step_diag.py` |

**Known failure:** `gatt.connect()` succeeds, then `gattserverdisconnected` in ~3–10 ms before service discovery. Host bleak often still **PASS** — that means firmware is OK; fix with OS pair + soft-blue + system Chrome/Edge.

**Verified 2026-07-18:** after Windows OS pair, `/diag` completed all steps green (through notify) with no errors.

---

## Chapter map

| Lab | Route | Title | Learns |
|-----|-------|--------|--------|
| 01 | `/labs/01` | Browser ready | Secure context + Web Bluetooth gate |
| 02 | `/labs/02` | Pick the board | `requestDevice` + `TESAIoT-` filter |
| 03 | `/labs/03` | Open the GATT link | GATT connect, chars, BS_LINK |
| 04 | `/labs/04` | Hear the first events | Notify + hybrid CFG + first EVT_SENSOR |
| 05 | `/labs/05` | Prove the stream | Continuous hybrid counters (all 6) |
| 06 | `/labs/06` | Steer one sensor | Fire-and-forget SENSOR_CFG_SET |
| 07 | `/labs/07` | Motion + climate | IMU + env cards |
| 08 | `/labs/08` | Knobs and buttons | ADC_POT + SW_BTN |
| 09 | `/labs/09` | Live board | Six-card compose + link + log |
| 10 | `/labs/10` | Your scaffold | Forkable template → `apps/dashboard` |

Each folder has a short `LAB.md`. Progress checkmarks are stored in `localStorage` (`tbs-ble-tutorial-progress-v1`).

Bring-up tool (not numbered): `/diag`.

---

## Tutorial UX

Shared kit under `apps/labs/src/tutorial/`:

- **TutorialShell** — left step rail + active step
- **Why / Do / Check** — explanation, actions, live acceptance gates
- **Callout** — tips / Windows warnings (ops text stays collapsed vs teaching)

Only `apps/*/src/transport/web-bluetooth.ts` may call `navigator.bluetooth` for production session code. Lab 02 and `/diag` call it directly for teaching / isolation.

---

## Packages

| Package | Role |
|---------|------|
| `@ternion/tbs-core` | UUIDs, CRC/frame, chunk reassembly, EVT decode (sensors 0–5) |
| `@ternion/tbs-ble-session` | `goLive`, CFG fire-and-forget, sample callbacks |

---

## Advanced (optional appendix)

Write Request vs Write Command, PING round-trip, waiting for POLICY/CFG RES — teach after the EVT path is solid. Not required for chapter acceptance.
