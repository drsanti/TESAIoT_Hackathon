# Node BLE bridge (host SimpleBLE → WebSocket)

Bypasses **Windows browser Web Bluetooth** for `ble-react` labs. Same board GATT; Node owns the radio.

## Run

```bash
# Terminal 1 — bridge (keep open)
cd TESAIoT_Hackathon/ble-react/tools/ble-bridge
npm install
npm start
# → ws://127.0.0.1:9788

# Terminal 2 — labs UI
cd TESAIoT_Hackathon/ble-react
pnpm --filter @ternion/tbs-labs dev
```

Then open **Edge or Chrome**:

`http://localhost:5174/?ble=bridge`

Or use the **Host bridge** toggle in the Connect bar. Soft-blue ADV; close other centrals (no competing `/diag` Web BLE).

## Protocol (JSON over WebSocket)

| Client → bridge | Bridge → client |
|-----------------|-----------------|
| `{ "type": "ping" }` | `{ "type": "pong" }` |
| `{ "type": "connect" }` | `{ "type": "connected", name, address, chars }` |
| `{ "type": "disconnect" }` | `{ "type": "disconnected" }` |
| `{ "type": "start_notify" }` | `{ "type": "notify", data: "<base64>" }` |
| `{ "type": "stop_notify" }` | |
| `{ "type": "write_rx", data: "<base64>", withResponse?: bool }` | `{ "type": "write_ok" }` |
| `{ "type": "read_link" }` | `{ "type": "link", data: "<base64>" }` |

Errors: `{ "type": "error", message }`.

Env: `TBS_BLE_BRIDGE_PORT` (default `9788`), `TBS_BLE_BRIDGE_HOST` (default `127.0.0.1`).

## Backend

**Default:** Node WebSocket control plane + **Python bleak worker** (`src/ble_worker.py` using `python-app/.venv`). Same WinRT radio path that already **ALL PASS** on this PC.

Optional SimpleBLE path remains in `ble-backend.mjs` (connect works; char enum often fails on Windows).

Env:
- `TBS_BLE_BRIDGE_PORT` (default `9788`)
- `TBS_BLE_BRIDGE_HOST` (default `127.0.0.1`)
- `TBS_BLE_PYTHON` — override path to Python with bleak installed

Requires: `TESAIoT_Hackathon/python-app/.venv` (same as `tools/ble_step_diag.py`).
