# Lab 04 — BS2 PING

## Learning goals

- Build / send a BS2 REQ and parse a RES
- Use `SessionLite.ping()` over the GATT pipe from Lab 03

## Concept

Same ATT path as Lab 03 (Write Command + Notify), now with the BS2 frame layout from [`../../docs/BS2_CHEATSHEET.md`](../../docs/BS2_CHEATSHEET.md).

## Hardware check

TFT soft-blue → connect → PONG

## Run

```bash
python labs/04_ping/lab.py
```

## Expected stdout

`PING → PONG status=0`

## Checkpoint questions

1. Which message TYPE is REQ vs RES?
2. Is the ATT write a Request or Command in this lab’s helper?

## Extend yourself

- Call `send_req(..., with_response=True)` and compare ATT latency to Lab 03

## Next lab

[`../05_sensor_cfg/`](../05_sensor_cfg/) — SENSOR_CFG for all six sensors
