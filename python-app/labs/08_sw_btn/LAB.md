# Lab 08 — Switches / buttons (SW_BTN)

## Learning goals

- Configure `sensorId=5` (SW_BTN)
- Decode `state` bitmask and per-button press **counts**
- See updates when you press BTN0–BTN2

## Concept

Payload is **not** packed i16:

```text
state u8
count u32 LE for each enabled mask bit (BTN0 → BTN2)
```

Default publish mode is **on_change**.

## Hardware check

Press **BTN0**, **BTN1**, **BTN2** on the AI kit while the lab runs.

## Run

```bash
python labs/08_sw_btn/lab.py
python labs/08_sw_btn/lab.py 25
```

## Expected stdout

Lines showing pressed buttons and cumulative counts when you press.

## Checkpoint questions

1. How many value bytes for `mask=0x07`?
2. Does `state` bit mean pressed or released?

## Extend yourself

- Detect rising edges in Python and print “BTN1 pressed” only once per press

## Next lab

[`../09_multisensor_app/`](../09_multisensor_app/) — all six on one CLI dashboard
