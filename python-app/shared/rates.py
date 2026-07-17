"""BLE-safe SENSOR_CFG timing for teaching labs.

Aggressive rates (tens of Hz on many sensors) can flood CM33 GATT/IPC and
freeze the TFT (WDT). Use ~1 Hz for periodic sensors in teaching labs.
On-change HMI sensors may sample faster; they only notify when values change.
"""

# Periodic IMU / environment (BMI270, BMM350, SHT40, DPS368)
TEACHING_PERIODIC_MS = 1000

# ADC_POT: sample faster for responsive pots; default publish is on_change
TEACHING_ADC_SAMPLE_MS = 200
TEACHING_ADC_DELTA_MV = 30
TEACHING_ADC_MIN_PUB_MS = 100

# SW_BTN: on_change; keep sample modest (not 20 ms)
TEACHING_BTN_SAMPLE_MS = 50

# Periodic smoke for HMI labs (--periodic) — still BLE-safe
TEACHING_HMI_PERIODIC_MS = 1000
