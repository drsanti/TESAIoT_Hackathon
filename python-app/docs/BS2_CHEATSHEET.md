# BS2 cheatsheet (labs)

## Frame skeleton

```text
"BS " | plen u16 LE | TYPE u8 | payload[plen] | CRC16 LE | CR LF
```

| TYPE | Meaning |
|-----:|---------|
| `0x02` | REQ |
| `0x03` | RES |
| `0x04` | EVT_SENSOR |

CRC-16/CCITT over `plen…payload` (see `shared/framing.py`).

## REQ payload

```text
reqId u16 LE | cmdId u8 | flags u8 | body…
```

## Common commands

| cmdId | Name |
|------:|------|
| `0x01` | PING |
| `0x10` | SENSOR_CFG_GET |
| `0x11` | SENSOR_CFG_SET |
| `0x35` | BLE_POLICY_GET |
| `0x36` | BLE_POLICY_SET |

## EVT_SENSOR header

```text
sensorId u8 | mask u8 | counter u32 LE | deviceMs u32 LE | values…
```

## SENSOR_CFG body (v2.1, 12 bytes)

```text
sensorId | enabled | publishMode | mask |
samplingIntervalMs u16 | deltaX100 u16 |
minPublishIntervalMs u16 | publishIntervalMs u16
```

| publishMode | Meaning |
|------------:|---------|
| 0 | periodic |
| 1 | on_change |
| 2 | hybrid |

## BLE policy flags (subset)

| Bit | Meaning |
|----:|---------|
| `0x01` | Advertise |
| `0x02` | TX EVT over BLE |
| `0x04` | RX REQ over BLE |

Factory streaming often uses `0x07` (ADV + TX_EVT + RX_REQ).

Quiet / config: labs often set **`0x05`** (ADV + RX_REQ, no TX_EVT) before `SENSOR_CFG`, then restore **`0x07`** to stream.

On disconnect, `SessionLite` restores teaching `SENSOR_CFG` for sensors **0–5** so the TFT does not stay on a single-sensor lab profile.

## Helpers

- Encode / parse: `shared/framing.py`
- Session: `shared/session_lite.py` (`restore_teaching_sensors`)
- Defaults: `shared/sensor_cfg_defaults.py`
- Decode EVT: `shared/decode.py`
