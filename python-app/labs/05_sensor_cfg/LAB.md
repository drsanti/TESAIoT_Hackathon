# Lab 05 — Focus one sensor

Fire-and-forget `SENSOR_CFG_SET` so only one sensor is enabled, then stream it.

```bash
python labs/05_sensor_cfg/lab.py                 # BMI270
python labs/05_sensor_cfg/lab.py 15 --focus 4    # pots (periodic)
python labs/05_sensor_cfg/lab.py --focus 5       # buttons (periodic)
```

**Next:** Labs 06 / 07 / 08 for domain detail.
