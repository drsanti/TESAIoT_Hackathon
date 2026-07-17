# BLE concepts (teaching)

## Roles

| Role | Who | Job |
|------|-----|-----|
| **Peripheral** | TESAIoT DevKit | Advertises `TESAIoT-*`, hosts the BS2 GATT service |
| **Central** | Your Python script (`bleak`) | Scans, connects, writes/reads/subscribes |

While no central is connected, the kit should keep advertising (TFT soft-blue). On connect, ADV stops and the TFT moves toward sky / cyan when streaming.

## ATT operations you will practice

| ATT op | Everyday name | Ack? | Bleak | Lab |
|--------|---------------|------|-------|-----|
| **Write Request** | Write with response | Yes — ATT Write Response | `write_gatt_char(..., response=True)` | **03** |
| **Write Command** | Write without response | No | `write_gatt_char(..., response=False)` | **03** (+ later BS2 TX) |
| **Notify** | Server → client push | No confirmation from client | `start_notify` | **03**+ |
| **Read** | Read Request | Yes | `read_gatt_char` | **02** |
| Indicate | Notify + confirmation | Yes | — | Not used on BS2 TX |

Firmware accepts both `GATT_REQ_WRITE` and `GATT_CMD_WRITE` on `BS_RX`. Streaming labs prefer **Write Command** for lower latency; use **Write Request** when you need an ATT-level delivery ack before continuing.

## CCCD (Client Characteristic Configuration Descriptor)

Notifications stay silent until the central enables them by writing the CCCD of `BS_TX` (Bleak’s `start_notify` does this). Lab 03 prints CCCD state before and after subscribe.

Without CCCD notify enable:

- Writes to `BS_RX` may still reach the firmware
- You will **not** see PONG / EVT_SENSOR on the host

## BS2 GATT characteristics

| Char | UUID suffix | Direction | Role |
|------|-------------|-----------|------|
| `BS_RX` | `…4001…` | Central → device | BS2 requests (and Lab 03 writes) |
| `BS_TX` | `…4002…` | Device → central | Responses and `EVT_SENSOR` (notify) |
| `BS_LINK` | `…4003…` | Read / notify | MTU, connection, drop counters |

Full UUIDs live in `shared/gatt_ids.py`.

## Wire prefix note

CM33 only forwards ATT writes that start with the BS2 prefix bytes `BS ` (`0x42 0x53 0x20`) into the BS2 path. Arbitrary “echo” payloads are ignored. Lab **03** therefore uses a real **PING** frame so Write Request / Write Command still produce a **Notify** (PONG) you can measure.

## How BS2 sits on GATT

After Lab 03 you treat the same pipe as a BS2 tunnel:

1. Build a BS2 frame (Lab 04+)
2. Write it to `BS_RX` (usually Write Command)
3. Reassemble notifications from `BS_TX`
4. Parse RES / EVT

Hands-on ATT lab: **`labs/03_gatt_ops/`**.

## Rate limits (do not flood BLE)

CM33 GATT + IPC cannot sustain high multi-sensor EVT rates. Too much traffic can freeze the TFT (WDT). Teaching labs use ~**1 Hz** periodic configs from `shared/rates.py`. Prefer **on_change** for pots/buttons.