# Web Bluetooth on Windows (Chrome / Edge)

Canonical bring-up notes for **ble-react** labs. v1 uses **browser Web Bluetooth only** (`navigator.bluetooth`) — not a host BLE bridge.

**Verified (2026-07-18):** After Windows OS pairing of `TESAIoT-*`, Chrome `/diag` completed **all steps green** once. On this same PC it later regressed to connect-then-drop (~10–100 ms). Prefer the **Node host bridge** when Web Bluetooth fails.

---

## Recommended on Windows: Node BLE bridge

Browser Web Bluetooth uses Chromium WinRT and often drops GATT immediately. Host Node SimpleBLE does not.

```bash
# Terminal 1
cd TESAIoT_Hackathon/ble-react/tools/ble-bridge
npm install && npm start
# ws://127.0.0.1:9788

# Terminal 2
cd TESAIoT_Hackathon/ble-react
pnpm --filter @ternion/tbs-labs dev
```

Open `http://localhost:5174/?ble=bridge` (or Connect bar → **Host bridge (Node)** → Connect). Soft-blue ADV; no competing Chrome GATT.

Details: [`tools/ble-bridge/README.md`](../tools/ble-bridge/README.md)

---

## Quick path (when labs fail after connect)

1. **Task Manager → End every `chrome.exe`** until count is **0**. Closing one tab is not enough; a leftover Chrome often owns WinRT BLE and Edge then drops GATT in ~2–10 ms.
2. Disconnect every other BLE central (nRF Connect, python-app). Prefer **Edge only** for the next try (do not reopen Chrome).
3. Board **RESET** (or TFT **Reset BLE**) until soft-blue (`TESAIoT-*` advertising).
4. **Windows Settings → Bluetooth**: remove old `TESAIoT-*` → Off 5s → On → **Add device** → pair until Paired.
5. System **Edge** (not Cursor’s embedded browser) → `http://localhost:5174/diag`.
6. Hard-reload → **Run all 1→6** once → pick the board.
7. When `/diag` is green, use the lab catalog Connect the same way.

---

## Fresh step diagnostic

| Stack | URL / command | Proves |
|-------|---------------|--------|
| **Browser Web Bluetooth** | `http://localhost:5174/diag` | Real Chrome/Edge WinRT path used by labs |
| Host Python (bleak) | `python-app/tools/ble_step_diag.py` | Firmware GATT / radio |
| Host Node (webbluetooth) | `ble-react/tools/webbluetooth-diag` | Browser-shaped API on host — **not** Chrome |

The `/diag` page does **not** use `useBleSession` / lab transport. Use it first when Lab 03+ fails.

Close browser GATT (**Disconnect** on `/diag`) before running host scripts (one central).

---

## Failure mode we saw

| Symptom | Typical cause |
|---------|----------------|
| Lab 01–02 OK; Lab 03+ / `/diag` fail | GATT opens then drops before discovery |
| `gatt.connect()` → `connected=true`, then `gattserverdisconnected` in **~3–10 ms** | Windows **browser** Web Bluetooth / WinRT — not lab UI logic |
| Error: `Bluetooth Device is no longer in range` | Stale `getDevices()` grant + **RPA address rotation** |
| Host bleak **ALL PASS**, Chrome drops after connect | Firmware OK; fix OS pair / browser path |
| Cursor IDE browser: PASS 1, stuck on requestDevice | Embedded **Electron** — use system Chrome/Edge |

Labs transport deliberately:

- Always uses a **fresh** `requestDevice` (does not prefer `getDevices()` — RPA invalidates old grants).
- Starts **service discovery immediately** after connect (no long post-connect settle sleep — that produced “disconnected during settle”).

---

## How to read cross-stack results

| Host bleak | Node webbluetooth | Chrome `/diag` | Meaning |
|------------|-------------------|----------------|---------|
| PASS | PASS (or PASS 1–4) | **PASS** | Web Bluetooth OK — run labs |
| PASS | PASS 1–4 | FAIL @ step 3 (~ms drop) | Firmware OK — Windows browser BLE; do OS pair + soft-blue |
| PASS | FAIL @ 5 (`0` chars) | — | SimpleBLE enum quirk — trust bleak for chars |
| FAIL @ scan | FAIL @ 2 | — | Board not advertising — RESET to soft-blue |

---

## Firmware notes (do not “fix” with bonding for Chrome alone)

- BS2 GATT is open (no AUTH required for teaching chars).
- Firmware stays **NO_BOND**. Enabling **SC_BOND** to chase Chrome broke **bleak** connect and was reverted.
- Host PASS after flash means on-device GATT is fine; remaining Chrome-only drops are a **browser / OS** issue.

---

## Agent / automation note

Cursor’s built-in browser reports `navigator.bluetooth` and can PASS step 1, but it is **not** a full Windows Chrome Web Bluetooth central. Automated agents cannot complete the device picker against real WinRT the same way a user can in system Chrome/Edge.

---

## Related

- Lab map: [LABS.md](./LABS.md)
- Python step diag: [`../../python-app/tools/README_BLE_STEP_DIAG.md`](../../python-app/tools/README_BLE_STEP_DIAG.md)
- Node step diag: [`../tools/webbluetooth-diag/README.md`](../tools/webbluetooth-diag/README.md)
- Transport: `apps/labs/src/transport/web-bluetooth.ts`
- Diag UI: `apps/labs/src/diag/BleStepDiagPage.tsx`
