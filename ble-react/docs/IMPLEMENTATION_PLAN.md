# Implementation plan — ble-react

**Version:** 0.1  
**Date:** 2026-07-11  
**Audience:** Developer continuing work on another machine

---

## 1. Before you start (handoff checklist)

### 1.1 Clone / copy repos

```bash
git clone https://github.com/drsanti/TESAIoT_Hackathon.git
cd TESAIoT_Hackathon/ble-react
```

Ensure sibling folders exist for reference (not runtime deps):

- `../ble-flet/bs2/` — Python session reference
- `../hex/` — firmware images
- `../web-app/` — MQTT/WS examples (future `tbs-mqtt-client` patterns)

Optional local clones for spec/constants:

- `Bitstream-Studio/extension/src/bitstream2/`
- `Bitstream-Studio/packages/bitstream-ble-client/`

### 1.2 Machine prerequisites

| Tool | Version |
|------|---------|
| Node.js | 20+ |
| pnpm | 9+ |
| Chrome or Edge | Web Bluetooth support |
| Git | LFS if pulling large HEX (optional) |

### 1.3 Hardware prerequisites

1. Flash `../hex/tesaiot-bitstream-*.hex`.
2. Enable BLE module profile `0x08` via Bitstream Studio UART once → reboot.
3. Confirm advertising: `TESAIoT-*` visible in nRF Connect (then disconnect nRF).

### 1.4 Read order

1. [README.md](../README.md)
2. [REQUIREMENTS.md](./REQUIREMENTS.md)
3. [ARCHITECTURE.md](./ARCHITECTURE.md)
4. [ADDONS.md](./ADDONS.md)
5. This file

---

## 2. Implementation phases

### Phase 0 — Scaffold monorepo (Day 1)

**Goal:** Empty workspace that builds; import boundaries enforced.

**Tasks:**

- [ ] Create `pnpm-workspace.yaml` with `packages/*` and `apps/*`
- [ ] Root `package.json` scripts: `build`, `test`, `dev`, `lint`
- [ ] Per-package `package.json` with scoped names:
  - `@ternion/tbs-core`
  - `@ternion/tbs-ble-session`
  - `@ternion/tbs-addon-kit`
  - `@ternion/tbs-example-led`
  - `@ternion/tbs-dashboard-demo` (private)
- [ ] Shared `tsconfig.base.json` (strict)
- [ ] tsup config per library package → `dist/` ESM + CJS + dts
- [ ] ESLint `no-restricted-imports` — `tbs-core` cannot import siblings
- [ ] Vitest workspace config

**Done when:** `pnpm install && pnpm build` succeeds (empty stubs OK).

---

### Phase 1 — `@ternion/tbs-core` (Days 2–4)

**Goal:** Protocol layer with tests; no BLE/React.

**Tasks:**

- [ ] `gatt.ts` — UUIDs from bitstream-ble-client / BLE_BS2.md
- [ ] `chunk.ts` — encode + `Bs2BleChunkReassembler` (port Python/TS reference)
- [ ] `wire.ts` — `encodeBsReq`, `tryParseBs2Frame`, CRC16-CCITT
- [ ] `commands.ts` — PING, BLE_POLICY, SENSOR_CFG cmdIds and flags
- [ ] `decode-sensor.ts` — EVT_SENSOR for four sensors
- [ ] `decode-link.ts` — BS_LINK body
- [ ] `rate.ts` — `authoritativeMeasHz()` from ble-flet session logic
- [ ] `registry.ts` — `DecoderRegistry` + `registerBuiltinDecoders()`
- [ ] `transport.ts` — `TbsFrameTransport` interface
- [ ] Copy `sensor-scene-presets.v1.json` from `ble-flet/bs2/`
- [ ] Tests: CRC golden, chunk multi-packet, EVT round-trip, custom decoder registration

**Reference files:**

- `../ble-flet/bs2/wire.py`, `chunk.py`, `decode.py`
- `Bitstream-Studio/packages/bitstream-ble-client/src/chunk.ts`

**Done when:** `pnpm --filter @ternion/tbs-core test` all pass.

---

### Phase 2 — `@ternion/tbs-addon-kit` (Days 4–5)

**Goal:** Extension API v1 before session is complete (drives session design).

**Tasks:**

- [ ] `api-version.ts` — `TBS_EXTENSION_API_V1 = 1`
- [ ] `define-addon.ts` — `defineTbsAddon`, `TbsAddon`, `TbsSessionPlugin` types
- [ ] `validateTbsAddon` — apiVersion, duplicate id
- [ ] `compose-session.ts` — wrap factory, merge hooks
- [ ] `mixins.ts` — `withSessionHooks`, `withFrameTap`
- [ ] `react-registry.ts` — `TbsUiRegistry`, `registerUiAddon`
- [ ] `react/shell.tsx` — minimal `TbsAppShell` (tabs placeholder)
- [ ] Tests: hook order, validation failures

**Done when:** Tests pass; types exported from `dist/`.

---

### Phase 3 — `@ternion/tbs-ble-session` (Days 5–8)

**Goal:** BLE session with fake transport tests.

**Tasks:**

- [ ] `transport.ts` — `TbsBleTransport` interface (GATT-level)
- [ ] `plugin-pipeline.ts` — run hooks in registration order
- [ ] `session.ts` — `createTbsBleSession`:
  - REQ/RES map + timeout
  - Chunk TX/RX integration with `tbs-core`
  - `BLE_POLICY_SET` 0x07 stream on
  - EVT_SENSOR dispatch, counter dedupe, deviceMs rate segments
- [ ] `connection-fsm.ts` — manual connect phases (Auto hunt = v2)
- [ ] `builtins/sensors.ts` — `registerBuiltinSensors()` add-on
- [ ] Fake transport test: loopback chunks → PING RES status 0

**Reference:** `../ble-flet/bs2/session.py`

**Done when:** `pnpm --filter @ternion/tbs-ble-session test` pass.

---

### Phase 4 — Web Bluetooth adapter + hardware smoke (Days 8–9)

**Goal:** Real DevKit PING over BLE.

**Tasks:**

- [ ] `apps/dashboard/src/transport/web-bluetooth.ts`
  - Only file using `navigator.bluetooth`
  - `requestDevice` filter `TESAIoT-`
  - Subscribe BS_TX; write BS_RX with chunking
- [ ] Vite HTTPS plugin or `http://localhost` for secure context
- [ ] Minimal CLI/page: Connect → PING → log result

**Done when:** Hardware PING returns RES status 0.

---

### Phase 5 — Dashboard UI (Days 9–12)

**Goal:** Reference app matching FR-UI requirements.

**Tasks:**

- [ ] `bootstrap.ts` — compose session + UI registry
- [ ] Zustand `session-store.ts` — subscribe to `SessionEvents`
- [ ] `useBleSession.ts` hook
- [ ] Pages: Connect, Live, Link, Log
- [ ] Built-in sensor cards via `registerBuiltinSensors` UI facet
- [ ] Scene preset chips (Motion default on connect)
- [ ] Rate line: meas vs cfg
- [ ] Live update throttle (~4 Hz) + toggle

**Done when:** Hardware smoke checklist (§4) passes.

---

### Phase 6 — Reference add-on (Days 12–13)

**Goal:** `@ternion/tbs-example-led` as copy template.

**Tasks:**

- [ ] Protocol: EVT_ACTUATOR LED decode in registry
- [ ] Session: `sendLedPulse()` helper
- [ ] UI: Link panel slot
- [ ] Wire into dashboard `bootstrap.ts`
- [ ] Document in [ADDONS.md](./ADDONS.md)

**Done when:** LED panel sends command; dashboard loads add-on.

---

### Phase 7 — Publish prep + docs (Day 14)

**Tasks:**

- [ ] `prepublishOnly` scripts on all packages
- [ ] README badges / install snippets
- [ ] Update `../README.md` (hackathon root) with `ble-react` section
- [ ] Optional: first publish to npm `@ternion` (requires org token)

**Done when:** Another machine can `npm install @ternion/tbs-core` and import types.

---

## 3. Dependency graph (build order)

```text
Phase 0 scaffold
    ↓
Phase 1 tbs-core
    ↓
Phase 2 tbs-addon-kit  ←──┐
    ↓                     │
Phase 3 tbs-ble-session ──┘
    ↓
Phase 4 web-bluetooth adapter
    ↓
Phase 5 dashboard
    ↓
Phase 6 tbs-example-led
    ↓
Phase 7 publish
```

---

## 4. Hardware smoke checklist

Run after Phase 5:

| # | Step | Expected |
|---|------|----------|
| 1 | Connect to `TESAIoT-*` | GATT linked; BS_TX notify enabled |
| 2 | PING | RES status 0 |
| 3 | Stream on | Policy flags 0x07 |
| 4 | Live cards | SHT40, DPS368, BMM350, BMI270 update |
| 5 | Motion preset | BMI270 meas ≈ cfg ±25% |
| 6 | Disconnect + reconnect | Clean re-link |

---

## 5. Dev commands (target)

```bash
# Install
pnpm install

# Unit tests
pnpm --filter @ternion/tbs-core test
pnpm --filter @ternion/tbs-ble-session test
pnpm --filter @ternion/tbs-addon-kit test

# Build all libraries
pnpm -r --filter './packages/*' build

# Dashboard dev (HTTPS for Web Bluetooth)
pnpm --filter dashboard dev
```

---

## 6. Risk register

| Risk | Mitigation |
|------|------------|
| Chrome notify batching skews rates | Use `deviceMs` + counter dedupe (ble-flet parity) |
| Web Bluetooth unavailable on Safari | Document Chrome/Edge only for v1 |
| Spec drift vs Bitstream Studio | `sync-bs2-constants.sh`; port tests from golden fixtures |
| Scope creep (Serial/MQTT) | v1 guardrail — ports in `tbs-core` only, no packages until v2 |
| npm `@ternion` scope access | Verify org token before Phase 7 |

---

## 7. v2 backlog (do not implement in v1)

- `@ternion/tbs-serial-session` + Web Serial
- `@ternion/tbs-mqtt-client`
- Auto hunt / reconnect FSM
- `BLE_TELEM_MODE` / `BLE_ADV_CTRL` add-ons
- `@ternion/tbs-react` extracted from addon-kit
- Electron transport
- `create-tbs-addon` CLI scaffold

---

## 8. File creation order (quick reference)

```text
1. pnpm-workspace.yaml, tsconfig, root package.json
2. packages/tbs-core/src/{gatt,chunk,wire,commands,decode-*,rate,registry,transport}.ts
3. packages/tbs-addon-kit/src/{api-version,define-addon,compose-session,mixins,react-registry}.ts
4. packages/tbs-ble-session/src/{transport,session,plugin-pipeline,connection-fsm,builtins}.ts
5. apps/dashboard/src/{bootstrap,transport/web-bluetooth,store,hooks,ui}
6. packages/tbs-example-led/src/index.ts
```

---

## 9. Sign-off

| Milestone | Owner | Date |
|-----------|-------|------|
| Docs handoff | — | 2026-07-11 |
| Phase 0 complete | | |
| v1 hardware smoke | | |
| npm publish | | |
