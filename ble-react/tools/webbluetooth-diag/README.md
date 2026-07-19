# Node Web Bluetooth step diagnostic

Uses [thegecko/webbluetooth](https://github.com/thegecko/webbluetooth) (Node + SimpleBLE).

Same steps as:

- Browser: `http://localhost:5174/diag`
- Python: `python-app/tools/ble_step_diag.py`

This does **not** patch Chrome. It only proves the **host** stack with a browser-shaped API.

## Run

```bash
cd TESAIoT_Hackathon/ble-react/tools/webbluetooth-diag
npm install
npm run diag
```

Close Chrome `/diag` and Python BLE labs first (one central).

## Observed on Windows (this machine)

Steps **1–4 often PASS** (API, scan, connect, BS2 service).  
Step **5 may FAIL** with `0 characteristics` — SimpleBLE under `webbluetooth` sometimes does not enumerate custom BS2 chars on WinRT even though the service UUID is visible.

For host **char / BS_LINK** proof, prefer:

```bash
cd TESAIoT_Hackathon/python-app
./.venv/Scripts/python.exe tools/ble_step_diag.py
```

For the **real labs path**, use system Chrome/Edge `/diag` after Windows OS pair — see [`docs/WEB_BLUETOOTH_WINDOWS.md`](../../docs/WEB_BLUETOOTH_WINDOWS.md).

**Verified 2026-07-18:** Chrome `/diag` all green after OS pair (Web Bluetooth OK). Host tools only help isolate firmware vs browser.

## Compare

| Python bleak | Node webbluetooth | Chrome /diag | Meaning |
|--------------|-------------------|--------------|---------|
| PASS | PASS 1–4 | **PASS** | Web Bluetooth OK — run labs |
| PASS | PASS 1–4 | FAIL @ 3 | Firmware OK — Windows **browser** Web Bluetooth; OS-pair |
| PASS | FAIL @ 5 (0 chars) | — | SimpleBLE enum quirk — trust bleak for chars |
| FAIL @ scan | FAIL @ 2 | — | Board not advertising |
