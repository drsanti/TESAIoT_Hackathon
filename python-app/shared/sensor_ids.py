"""Sensor IDs and default masks for teaching labs."""

from __future__ import annotations

SENSOR_BMI270 = 0
SENSOR_BMM350 = 1
SENSOR_SHT40 = 2
SENSOR_DPS368 = 3
SENSOR_ADC_POT = 4
SENSOR_SW_BTN = 5

SENSOR_NAMES = {
    SENSOR_BMI270: "BMI270",
    SENSOR_BMM350: "BMM350",
    SENSOR_SHT40: "SHT40",
    SENSOR_DPS368: "DPS368",
    SENSOR_ADC_POT: "ADC_POT",
    SENSOR_SW_BTN: "SW_BTN",
}

# Typical teaching masks
DEFAULT_MASKS = {
    SENSOR_BMI270: 0x03,  # accel + gyro
    SENSOR_BMM350: 0x03,  # mag + temp
    SENSOR_SHT40: 0x03,  # temp + humidity
    SENSOR_DPS368: 0x03,  # pressure + temp
    SENSOR_ADC_POT: 0x0F,  # POT1–4
    SENSOR_SW_BTN: 0x07,  # BTN0–2
}

ADC_POT_MASK = {"POT1": 0x01, "POT2": 0x02, "POT3": 0x04, "POT4": 0x08, "ALL": 0x0F}
SW_BTN_MASK = {"BTN0": 0x01, "BTN1": 0x02, "BTN2": 0x04, "ALL": 0x07}

ALL_SENSOR_IDS = tuple(range(6))
