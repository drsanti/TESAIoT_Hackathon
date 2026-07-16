# Lab 06 — EVT stream (IMU & environment)

## Learning goals

- Enable BLE EVT policy and SENSOR_CFG for sensors **0–3**
- Decode live `EVT_SENSOR` samples for BMI270, BMM350, SHT40, DPS368

## Concept

After CCCD notify + policy TX_EVT, the kit pushes EVT frames on `BS_TX`. Move the board to see accel / gyro change.

## Hardware check

- Lab 04 PING works
- TFT may show cyan while streaming

## Run

```bash
python labs/06_stream_imu_env/lab.py
# optional: duration seconds
python labs/06_stream_imu_env/lab.py 20
```

## Expected stdout

Live lines for BMI270 / BMM350 / SHT40 / DPS368 for several seconds.

## Checkpoint questions

1. Which ATT op delivers EVT bytes to your script?
2. What scales are used for accel vs humidity?

## Extend yourself

- Print measured Hz per sensor from counter / deviceMs

## Next lab

[`../07_adc_pot/`](../07_adc_pot/) — turn potentiometers
