# Lab 07 — Potentiometers (ADC_POT)

## Learning goals

- Configure `sensorId=4` (ADC_POT) with mask `0x0F`
- Decode millivolt values for POT1–POT4
- See values change when you turn pots

## Concept

Packed `i16` millivolts. Prefer `publishMode=1` (on_change) with `delta_x100` as mV deadband so the console is quiet until you turn a pot.

## Hardware check

AI kit pots accessible. Turn **POT1–POT4** while the lab runs.

## Run

```bash
python labs/07_adc_pot/lab.py
python labs/07_adc_pot/lab.py 30
```

## Expected stdout

Lines like `POT1=812 mV …` updating as you turn knobs.

## Checkpoint questions

1. What unit is on the wire for ADC_POT?
2. How does `delta_x100` differ from SHT40’s scaled fields?

## Extend yourself

- Use hybrid mode with a 500 ms periodic floor

## Next lab

[`../08_sw_btn/`](../08_sw_btn/) — press buttons
