# Lab 02 — Connect & discover (Read)

## Learning goals

- Connect as a BLE central
- Discover the BS2 service and characteristic **properties**
- Perform an ATT **Read** on `BS_LINK`

## BLE concept

After connect, the peripheral stops advertising. Characteristics expose properties such as `read`, `write`, `write-without-response`, `notify`. Lab 03 uses write + notify; this lab focuses on **Read**.

## Hardware check

- TFT soft-blue before connect → sky (connected) after success

## Run

```bash
python labs/02_connect/lab.py
```

## Expected stdout

- Device name / address
- `BS_RX` / `BS_TX` / `BS_LINK` with property lists
- `BS_LINK` snapshot (state, mtu, optional tx_drops)

## Checkpoint questions

1. Which characteristic is notify-capable?
2. Which characteristic do you **read** for link status?
3. Does Write Request or Write Command appear in `BS_RX` properties?

## Extend yourself

- Also try `start_notify` on `BS_LINK` if the property list includes notify
- Disconnect and confirm TFT returns to soft-blue advertising

## Next lab

[`../03_gatt_ops/`](../03_gatt_ops/) — Write Request, Write Command, Notify + CCCD
