# Sensor catalog (all six BS2 wire sensors)

| Id | Name | Mask (typical) | Values | Lab |
|---:|------|----------------|--------|-----|
| 0 | BMI270 | `0x03` accel+gyro | packed `i16` (scaled) | 05, **06**, 09 |
| 1 | BMM350 | `0x03` mag+temp | packed `i16` | 05, **06**, 09 |
| 2 | SHT40 | `0x03` temp+humidity | packed `i16` ×100 | 05, **06**, 09 |
| 3 | DPS368 | `0x03` pressure+temp | packed `i16` | 05, **06**, 09 |
| 4 | **ADC_POT** | `0x0F` POT1–4 | packed `i16` **mV** | 05, **07**, 09 |
| 5 | **SW_BTN** | `0x07` BTN0–2 | `state u8` + `count u32` each | 05, **08**, 09 |

## ADC_POT (`sensorId=4`)

| Bit | Field | Notes |
|----:|-------|-------|
| `0x01` | POT1 | millivolts |
| `0x02` | POT2 | |
| `0x04` | POT3 | |
| `0x08` | POT4 | |

`deltaX100` is a **millivolt** deadband for on_change / hybrid.

## SW_BTN (`sensorId=5`)

Payload is **not** packed i16:

```text
state u8
for each enabled mask bit (BTN0→BTN2):
  count u32 LE
```

| Bit | Button |
|----:|--------|
| `0x01` | BTN0 |
| `0x02` | BTN1 |
| `0x04` | BTN2 |

`state` bit set = pressed.

## Passport (Lab 05)

Fill while running Lab 05:

| Id | Enabled? | Mode | Mask | Sample ms | Notes |
|---:|----------|------|------|-----------|-------|
| 0 | | | | | |
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
