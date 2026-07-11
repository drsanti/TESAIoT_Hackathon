# ble-react — Ternion BitStream BLE client (React)

Publishable **React + TypeScript** monorepo for talking to **TESAIoT firmware over BLE** (Web Bluetooth). v1 ships a reference dashboard; core libraries publish to npm as **`@ternion/tbs-*`**.

**Status:** Documentation and scaffold plan only — implementation starts on a fresh machine.

---

## Documentation (read in order)

| Doc | Purpose |
|-----|---------|
| [docs/REQUIREMENTS.md](./docs/REQUIREMENTS.md) | Functional / non-functional requirements, v1 scope, acceptance tests |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Layers, packages, naming (BS2 / TBS / BLE), multi-transport roadmap |
| [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) | Phased build order, tasks, handoff checklist for new machine |
| [docs/ADDONS.md](./docs/ADDONS.md) | Extension API v1 — `defineTbsAddon`, mixins, third-party packages |

---

## What this repo is

| Sibling in hackathon | Role |
|----------------------|------|
| [`../web-app/`](../web-app/) | HTML demos via Bitstream Studio telemetry (WS / MQTT) — **no direct BLE** |
| [`../ble-flet/`](../ble-flet/) | Desktop BLE dashboard (Python Flet + bleak) |
| **`ble-react/`** | Browser BLE dashboard + **npm libraries** for React developers |

---

## npm packages (published from `packages/`)

| Package | Role |
|---------|------|
| `@ternion/tbs-core` | BS2 wire encode/decode (transport-agnostic) |
| `@ternion/tbs-ble-session` | BLE GATT session orchestration |
| `@ternion/tbs-addon-kit` | `defineTbsAddon`, UI registry, `composeSession` |
| `@ternion/tbs-example-led` | Reference add-on (optional publish) |

`apps/dashboard` is a **private** reference app — not published.

---

## Firmware prerequisites

1. Flash HEX from [`../hex/`](../hex/) (match VSIX/firmware version).
2. One-time: enable **BLE module profile** bit `0x08` in Bitstream Studio → Runtime health → **reboot** (UART step). The React app does **not** require Studio at runtime.
3. Disconnect other BLE centrals (nRF Connect, ble-flet).
4. Use **Chrome or Edge** with Web Bluetooth; dev server on `https://localhost` or `http://localhost`.

Normative BLE spec (external): Bitstream Studio [`BLE_BS2.md`](https://github.com/drsanti/Bitstream-Studio/blob/main/extension/src/bitstream2/docs/BLE_BS2.md) (or local clone under `Bitstream-Studio/extension/`).

---

## Quick start (after implementation)

```bash
cd TESAIoT_Hackathon/ble-react
pnpm install
pnpm --filter @ternion/tbs-core test
pnpm --filter dashboard dev
```

Open the Vite URL in Chrome; use **Connect** → pick `TESAIoT-*` → **Stream on** → verify Live sensor cards.

---

## Reference code to port (do not import at runtime)

| Source | Use for |
|--------|---------|
| [`../ble-flet/bs2/`](../ble-flet/bs2/) | Session flow, rate math (`deviceMs`), scene presets |
| Bitstream Studio `packages/bitstream-ble-client` | GATT UUIDs, chunk envelope v1 |
| Bitstream Studio `extension/src/bitstream2/domains/ble/` | Policy / telem cmdIds and flags |

**Rule:** `ble-react` must **not** depend on `Bitstream-Studio/extension/` at build time — copy constants and logic into `@ternion/tbs-core`.

---

## License

TBD — align with TESAIoT Hackathon / Ternion policy when publishing `@ternion/*` packages.
