# Lab 10 — Build your own

## Learning goals

- Start from a minimal scaffold
- Choose sensors from each class and ship a tiny app of your own

## Checklist (required)

Pick **at least one** from each class:

| Class | Options | Your choice |
|-------|---------|-------------|
| IMU | BMI270, BMM350 | ________ |
| Environment | SHT40, DPS368 | ________ |
| HMI | ADC_POT, SW_BTN | ________ |

Ideas:

- Alarm when humidity > threshold **and** a button is held
- “Theremin”: map POT1 to printed bar length while showing gyro
- Button-gated logger: only print IMU while BTN0 is pressed

## Hardware check

Same as Lab 09.

## Run (scaffold)

```bash
python labs/10_your_app/lab.py
```

Edit `lab.py` — replace the TODO section with your logic.

## Expected stdout

Whatever you design — plus a clear SUCCESS line when your exit condition is met.

## Checkpoint questions

1. Which write mode does the scaffold use for BS2 requests?
2. Why must CCCD notify stay enabled?

## Extend yourself

- Package your app as a teammate demo with a short README in this folder

## Done

You completed the BLE → GATT ATT → BS2 → full sensor path. Optional: explore [`../../ble-flet/`](../../ble-flet/) for a desktop UI.
