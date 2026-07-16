# Lab 05 — SENSOR_CFG (all six sensors)

## Learning goals

- GET and SET `SENSOR_CFG` for **sensorId 0–5**
- Fill the sensor passport in [`../../docs/SENSOR_CATALOG.md`](../../docs/SENSOR_CATALOG.md)

## Concept

Config is separate from streaming. This lab prints / lightly enables each sensor; Labs 06–08 stream subsets.

## Hardware check

PING works (Lab 04). Prefer quiet environment (one central).

## Run

```bash
python labs/05_sensor_cfg/lab.py
```

## Expected stdout

A table for ids 0–5 with enabled, mode, mask, sample/publish intervals. SET echoes accepted.

## Checkpoint questions

1. Which sensor uses a non-i16 EVT payload?
2. What does `publishMode=1` mean?

## Extend yourself

- Disable all sensors, then enable only SHT40 at 1 Hz

## Next lab

[`../06_stream_imu_env/`](../06_stream_imu_env/) — live IMU + environment EVT
