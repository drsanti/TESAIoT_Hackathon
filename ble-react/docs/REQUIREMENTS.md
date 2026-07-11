# Requirements — ble-react / `@ternion/tbs-*`

**Version:** 0.1 (planning)  
**Date:** 2026-07-11  
**Status:** Approved for implementation handoff

---

## 1. Purpose

Deliver a **browser-based BLE client** for TESAIoT DevKit firmware and a **publishable TypeScript SDK** so third-party developers can build React (or non-React) apps without forking Bitstream Studio.

v1 focuses on **BLE via Web Bluetooth**. The SDK architecture must support **Web Serial** and **MQTT** in future packages without breaking `@ternion/tbs-core` or add-ons.

---

## 2. Stakeholders

| Stakeholder | Need |
|-------------|------|
| Hackathon participants | Connect phone/laptop to DevKit over BLE; see live sensors |
| External React developers | Install `@ternion/tbs-*` from npm; extend via add-ons |
| Ternion maintainers | One product line (`tbs`) aligned with BS2 firmware spec |

---

## 3. Functional requirements

### 3.1 Connection (FR-CONN)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CONN-1 | User can pick a BLE peripheral advertising `TESAIoT-*` via Web Bluetooth | P0 |
| FR-CONN-2 | App discovers GATT service `6f6b7a80-0001-4000-8000-00805f9b34fb` and chars BS_RX / BS_TX / BS_LINK | P0 |
| FR-CONN-3 | User can disconnect cleanly; GATT link releases for other centrals | P0 |
| FR-CONN-4 | App shows a clear error when Web Bluetooth is unavailable (browser / secure context) | P0 |

### 3.2 Protocol (FR-PROTO)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-PROTO-1 | BS2 frames use the same `BS ` envelope + CRC16-CCITT as UART (per BS2 spec) | P0 |
| FR-PROTO-2 | BLE path uses ATT chunk envelope v1 before BS2 frame reassembly | P0 |
| FR-PROTO-3 | REQ/RES correlation by `reqId`; PING returns RES status 0 | P0 |
| FR-PROTO-4 | Decode `EVT_SENSOR` for SHT40, DPS368, BMM350, BMI270 | P0 |
| FR-PROTO-5 | `BLE_POLICY_SET` with flags `0x07` (ADV + TX_EVT + RX_REQ) enables sensor stream | P0 |
| FR-PROTO-6 | Read BS_LINK snapshot (MTU, connection state, tx_drops) | P1 |
| FR-PROTO-7 | Apply sensor scene presets (Motion / Realtime / Lab Quiet) via SENSOR_CFG | P1 |

### 3.3 Dashboard UI (FR-UI)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UI-1 | **Connect** screen: prerequisites checklist + Connect button | P0 |
| FR-UI-2 | **Live** screen: four sensor cards with latest values | P0 |
| FR-UI-3 | **Link** screen: PING, Stream on/off, link stats, scene preset chips | P1 |
| FR-UI-4 | **Log** screen: timestamped session diagnostics; copy to clipboard | P1 |
| FR-UI-5 | Rate line per sensor: `meas` (counter ÷ MCU `deviceMs`) vs `cfg` (SENSOR_CFG) | P1 |
| FR-UI-6 | Throttle Live UI updates (~4 Hz default); optional “update on every EVT” toggle | P2 |

### 3.4 Extensibility (FR-EXT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EXT-1 | Third parties can ship npm add-ons via `defineTbsAddon()` | P0 |
| FR-EXT-2 | Add-ons can register protocol decoders, session hooks, and UI slots | P0 |
| FR-EXT-3 | `validateTbsAddon()` rejects duplicate ids and API version mismatch at bootstrap | P0 |
| FR-EXT-4 | Reference add-on `@ternion/tbs-example-led` demonstrates LED path | P1 |

### 3.5 Publishing (FR-PUB)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-PUB-1 | `packages/*` build to `dist/` (ESM + CJS + `.d.ts`) and publish under `@ternion` scope | P0 |
| FR-PUB-2 | `apps/dashboard` is private and not published | P0 |
| FR-PUB-3 | Packages installable without Bitstream Studio or hackathon monorepo | P0 |

---

## 4. Non-functional requirements

### 4.1 Architecture (NFR-ARCH)

| ID | Requirement |
|----|-------------|
| NFR-ARCH-1 | **Protocol layer** (`tbs-core`) has zero dependency on BLE APIs, React, or `navigator.*` |
| NFR-ARCH-2 | **Only** `apps/dashboard/src/transport/web-bluetooth.ts` may call `navigator.bluetooth` |
| NFR-ARCH-3 | Import boundaries enforced (ESLint / package `exports`) — no upward imports |
| NFR-ARCH-4 | Session logic testable with fake in-memory transport (no hardware in unit tests) |

### 4.2 Performance (NFR-PERF)

| ID | Requirement |
|----|-------------|
| NFR-PERF-1 | UI remains responsive at default sensor rates (~1–10 Hz per sensor) |
| NFR-PERF-2 | Rate display uses authoritative `deviceMs` span — not wall-clock notify count alone (see ble-flet) |
| NFR-PERF-3 | Detect EVT counter reset after SENSOR_CFG; do not double-count recycled seq values |

### 4.3 Compatibility (NFR-COMPAT)

| ID | Requirement |
|----|-------------|
| NFR-COMPAT-1 | Chrome and Edge desktop; Android Chrome for Web Bluetooth |
| NFR-COMPAT-2 | Node 20+ for build tooling; TypeScript strict |
| NFR-COMPAT-3 | Firmware: BLE module profile enabled; advertising `TESAIoT-<MAC4>` |

### 4.4 Security (NFR-SEC)

| ID | Requirement |
|----|-------------|
| NFR-SEC-1 | Web Bluetooth requires secure context (HTTPS or localhost) |
| NFR-SEC-2 | No remote add-on loading — add-ons are npm packages composed at build time |

---

## 5. Out of scope (v1)

- Electron / bleak desktop client
- React Native BLE
- Auto hunt / reconnect FSM (ble-flet parity) — v2
- `BLE_TELEM_MODE` Stop/Idle/Normal UI — v2 add-on
- `BLE_ADV_CTRL` restart UI — v2 add-on
- `@ternion/tbs-serial-session` / `@ternion/tbs-mqtt-client` implementation — v2+ (ports documented only)
- Bitstream Studio VSIX integration
- Dynamic plugin store / runtime URL loading

---

## 6. Acceptance criteria (v1 done)

### Hardware smoke (manual)

1. **Connect** → PING → RES status 0 within timeout.
2. **Stream on** → all four Live cards update within 10 s.
3. **Motion preset** → BMI270 `meas` within ±25% of `cfg` for 30 s soak.
4. **Disconnect** → reconnect works; no stuck GATT from prior session.
5. Only one central connected (ble-flet / nRF Connect disconnected).

### Automated (CI)

1. `pnpm --filter @ternion/tbs-core test` — CRC goldens, chunk reassembly, EVT decode.
2. `pnpm --filter @ternion/tbs-ble-session test` — fake transport PING + stream policy encode path.
3. `pnpm --filter @ternion/tbs-addon-kit test` — `defineTbsAddon` + `composeSession` ordering.
4. `pnpm build` — all packages emit `dist/` without TypeScript errors.

---

## 7. External specifications

| Document | Location |
|----------|----------|
| BLE GATT + policy | Bitstream Studio `extension/src/bitstream2/docs/BLE_BS2.md` |
| BS2 wire envelope | Bitstream Studio `extension/docs/BITSTREAM_BS_FRAMED_PROTOCOL_SPEC.md` |
| SENSOR_CFG | Bitstream Studio `extension/src/bitstream2/docs/SENSOR_CFG_V2.md` |
| Firmware BLE handoff | `TESAIoT_Library/CM33_NS/modules/cm33_ble_peripheral/BLE_PERIPHERAL_AGENT_HANDOFF.md` |
| Python reference session | `TESAIoT_Hackathon/ble-flet/bs2/session.py` |

---

## 8. Glossary

| Term | Meaning |
|------|---------|
| **BS2** | BitStream wire protocol (`BS ` frames) — transport-agnostic |
| **TBS** | Ternion BitStream — npm product line `@ternion/tbs-*` |
| **BLE** | Bluetooth Low Energy GATT path (this v1 client) |
| **Add-on** | npm package extending protocol/session/UI via `defineTbsAddon` |
| **Mixin** | Lightweight hook wrapper without a full package |
