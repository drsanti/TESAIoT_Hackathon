# Lab 04 - Hear the first events

## Goal

Enable BS_TX notifications, apply hybrid SENSOR_CFG, and decode at least one `EVT_SENSOR`.

## On-screen steps

1. Stay connected (reuse Chapter 03 session - avoid Disconnect/reconnect on Windows).
2. **Start notifications** (`goLive` + hybrid `SENSOR_CFG_SET`).

## Acceptance

Phase `live` + ≥1 decoded EVT → chapter complete.

## Notes

EVT-first: CCCD arms `TX_EVT`; hybrid CFG makes sensors publish. No PING/POLICY wait. Euler/quat appear after BMI270 fusion CFG (Lab 07) or Studio.

If Connect fails after Lab 03: use TFT **Reset BLE**, soft-blue ADV, then Start notifications once (prefer keeping the linked session).
