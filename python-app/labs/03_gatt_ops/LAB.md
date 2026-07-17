# Lab 03 — Go live (first EVTs)

Enable `BS_TX` notify. Firmware opens `TX_EVT` on CCCD. Print the first decoded `EVT_SENSOR` samples.

No PING / no Write Request teaching — continuous data uses Notify only.

```bash
python labs/03_gatt_ops/lab.py
python labs/03_gatt_ops/lab.py 10
```

**Next:** Lab 04 (continuous stream).
