# Fresh BLE step diagnostic

Independent of ble-react `useBleSession` / `web-bluetooth.ts` and of `SessionLite`.

## 1) Host (Python / bleak) — proves firmware

```bash
cd TESAIoT_Hackathon/python-app
./.venv/Scripts/python.exe tools/ble_step_diag.py
```

Steps: scan → connect → BS2 service → chars → read BS_LINK → notify enable.
Always disconnects at the end.

## 2) Host (Node / webbluetooth) — same API shape as browser

Uses [thegecko/webbluetooth](https://github.com/thegecko/webbluetooth) in **Node** (not Chrome):

```bash
cd TESAIoT_Hackathon/ble-react/tools/webbluetooth-diag
npm install
npm run diag
```

## 3) Browser (Chrome / Edge) — proves Web Bluetooth

Open: http://localhost:5174/diag

Use **Run all 1→6** (or click steps). This page does **not** use the lab session provider.

**Windows:** pair `TESAIoT-*` in **Settings → Bluetooth** before Run all if step 3 drops in a few ms. Full notes: [`ble-react/docs/WEB_BLUETOOTH_WINDOWS.md`](../../ble-react/docs/WEB_BLUETOOTH_WINDOWS.md).

**Verified 2026-07-18:** after OS pair, Chrome `/diag` all green (through notify).

## How to read results

| Host Python | Node webbluetooth | Chrome /diag | Meaning |
|-------------|-------------------|--------------|---------|
| PASS | PASS | PASS | Stack OK — proceed with labs |
| PASS | PASS | FAIL @ step 3 (~ms drop) | Firmware OK — Windows browser Web Bluetooth; OS-pair + soft-blue |
| FAIL @ step 1 | FAIL @ 2 | — | Board not advertising — RESET to soft-blue |

Close Chrome GATT (Disconnect on /diag) before running host scripts.
