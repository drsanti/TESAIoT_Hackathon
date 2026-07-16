# Lab 03 — GATT ATT ops (Write Request, Write Command, Notify)

## Learning goals

- Enable **Notify** on `BS_TX` via CCCD (`start_notify`)
- Send a **Write Request** (`response=True`) and wait for the ATT ack
- Send a **Write Command** (`response=False`) with no ATT ack
- Compare timing and understand when each write mode is useful

## BLE concept

| Op | Bleak | ATT ack? |
|----|-------|----------|
| Write Request | `response=True` | Yes |
| Write Command | `response=False` | No |
| Notify | `start_notify` | No (server → you) |

Firmware only forwards `BS_RX` payloads that start with the BS2 prefix (`BS `). This lab therefore writes a real **PING** frame so you still get a **Notify** (PONG) after each write mode.

See [`../../docs/BLE_CONCEPTS.md`](../../docs/BLE_CONCEPTS.md).

## Hardware check

- One central only
- TFT → sky after connect; soft-blue again after disconnect

## Run

```bash
python labs/03_gatt_ops/lab.py
```

## Expected stdout

1. CCCD before subscribe → after subscribe (`notify`)
2. Write Request: ATT write elapsed ms, then PONG notify ms, status 0
3. Write Command: ATT write elapsed (usually smaller), then PONG notify ms, status 0
4. Timing contrast summary

## Checkpoint questions

1. Which write mode waits for an ATT Write Response before `write_gatt_char` returns?
2. Why do streaming labs usually prefer Write Command?
3. What happens if you write without enabling CCCD notify?

## Extend yourself

- Run Write Command ten times in a tight loop and count PONG arrivals
- Try `response=True` for a large SENSOR_CFG_SET in a later lab and note latency

## Next lab

[`../04_ping/`](../04_ping/) — wrap PING in the session helper (BS2 REQ/RES)
