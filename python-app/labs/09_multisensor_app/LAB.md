# Lab 09 — Multi-sensor mini-app

## Learning goals

- Enable **all six** sensors on one connection
- Maintain a live CLI “dashboard” of latest values
- Combine IMU, environment, pots, and buttons in one app

## Concept

This is a small real application: connect → notify → policy → configure → render latest samples until Ctrl+C or timeout.

## Hardware check

Move board, turn pots, press buttons during the run.

## Run

```bash
python labs/09_multisensor_app/lab.py
python labs/09_multisensor_app/lab.py 40
```

## Expected stdout

A refreshing block (or scrolling lines) showing BMI270, BMM350, SHT40, DPS368, ADC_POT, SW_BTN.

## Checkpoint questions

1. Which sensors are on_change by default in this lab?
2. How would you mute IMU but keep pots?

## Extend yourself

- Write CSV of samples to a file
- Add a simple threshold alarm when any pot > 1500 mV

## Next lab

[`../10_your_app/`](../10_your_app/) — build your own template
