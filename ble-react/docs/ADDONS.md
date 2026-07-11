# Add-ons — Extension API v1

**Package:** `@ternion/tbs-addon-kit`  
**Contract version:** `TBS_EXTENSION_API_V1 = 1`  
**Date:** 2026-07-11

---

## 1. Overview

Third-party developers extend Ternion BitStream clients without forking `@ternion/tbs-core` or `@ternion/tbs-ble-session`.

Two mechanisms:

| Mechanism | When to use |
|-----------|-------------|
| **Add-on** (`defineTbsAddon`) | Publishable npm package (protocol + session + optional UI) |
| **Mixin** (`withSessionHooks`) | One-off behavior tweak inside your app |

Add-ons are **imported at app bootstrap** — no runtime download from URLs.

---

## 2. Minimal add-on

```ts
import { defineTbsAddon } from "@ternion/tbs-addon-kit";

export function registerMyAddon() {
  return defineTbsAddon({
    id: "my-addon",
    apiVersion: 1,
    protocol(registry) {
      // optional: registry.registerSensorMapper(...)
    },
    session: {
      hooks: {
        afterConnect(ctx) {
          ctx.log("info", "My add-on connected");
        },
        onSample(sensorId, sample) {
          // inspect or forward samples
        },
      },
    },
  });
}
```

---

## 3. `defineTbsAddon` shape

```ts
interface TbsAddonDefinition {
  id: string;                    // unique, kebab-case
  apiVersion: 1;                 // must match TBS_EXTENSION_API_V1
  protocol?: (registry: DecoderRegistry) => void;
  session?: {
    hooks?: TbsSessionPlugin["hooks"];
    helpers?: Record<string, unknown>;  // optional exported helpers
  };
  ui?: (registry: TbsUiRegistry) => void;
}
```

`validateTbsAddon(addon)` checks:

- `apiVersion === TBS_EXTENSION_API_V1`
- `id` non-empty and unique in the add-on list
- No duplicate `id` across registered add-ons

---

## 4. Session hooks

Run in **registration order** unless noted.

| Hook | When | Notes |
|------|------|-------|
| `beforeConnect` | Before GATT connect | Async allowed |
| `afterConnect` | GATT ready, before PING | Good for initial REQ |
| `onTxFrame` | Before write to transport | Return replaced `Uint8Array` or void; chain L→R, last replace wins |
| `onRxFrame` | After reassemble, before decode | Observe raw BS2 frames |
| `onSample` | After EVT_SENSOR decode | Same `SensorSample` type as built-ins |
| `onPhase` | Connection FSM transition | idle / linked / live / … |

---

## 5. Protocol registry (`@ternion/tbs-core`)

Add-ons receive `DecoderRegistry` in `protocol.setup`:

```ts
protocol(registry) {
  registry.registerResBodyDecoder(0x57, decodeRgbPanelRes);
  registry.registerSensorMapper(4, mapCustomSensor);
}
```

Built-in decoders register first via `registerBuiltinDecoders()`. Add-on registration must not override built-in cmdIds without explicit intent (document conflicts).

---

## 6. UI registry (`@ternion/tbs-addon-kit/react`)

```ts
import { createUiRegistry, registerUiAddon } from "@ternion/tbs-addon-kit/react";

const ui = createUiRegistry();

registerUiAddon(ui, {
  id: "my-addon",
  sensorCards: [
    {
      sensorId: "sht40",
      priority: 10,
      render: (props) => <MySht40Card {...props} />,
    },
  ],
  linkPanels: [
    { id: "my-tools", render: MyToolsPanel },
  ],
  toolbarActions: [
    { id: "refresh", label: "Refresh", onClick: () => {} },
  ],
  routes: [
    { path: "/extra", label: "Extra", element: ExtraPage },
  ],
});
```

`TbsAppShell` renders registered slots. Built-in sensor cards **must** use the same API (dogfooding).

---

## 7. App bootstrap

```ts
import { composeSession, createUiRegistry } from "@ternion/tbs-addon-kit";
import { createTbsBleSession, registerBuiltinSensors } from "@ternion/tbs-ble-session";
import { registerLedAddon } from "@ternion/tbs-example-led";
import { createWebBluetoothTransport } from "./transport/web-bluetooth";

const addons = [
  registerBuiltinSensors(),
  registerLedAddon(),
  registerMyAddon(),
];

for (const a of addons) validateTbsAddon(a);

const session = composeSession(createTbsBleSession, addons);
const ui = createUiRegistry();
addons.forEach((a) => a.ui?.(ui));

// on Connect:
await session.connect(createWebBluetoothTransport());
```

---

## 8. Publishing your add-on

**Package naming:** `@your-scope/tbs-addon-<feature>`

**peerDependencies:**

```json
{
  "@ternion/tbs-core": "^1.0.0",
  "@ternion/tbs-ble-session": "^1.0.0",
  "@ternion/tbs-addon-kit": "^1.0.0",
  "react": "^19.0.0"
}
```

`react` only required if you ship `ui.tsx`.

**Layout:**

```text
@acme/tbs-addon-foo/
├── package.json
├── src/
│   ├── protocol.ts
│   ├── session.ts
│   ├── ui.tsx          # optional
│   └── index.ts        # export registerFooAddon()
└── README.md
```

---

## 9. Reference add-on: `@ternion/tbs-example-led`

Ships in `packages/tbs-example-led/`:

1. **protocol** — `EVT_ACTUATOR` LED done decoder
2. **session** — `sendLedPulse(session, ledId, count)` helper
3. **ui** — Link tab LED panel

Copy this package when starting a new add-on.

---

## 10. Versioning policy

| Change | Bump |
|--------|------|
| New optional hook | `tbs-addon-kit` minor; API version unchanged |
| Hook signature break | `tbs-addon-kit` major; `TBS_EXTENSION_API_V2` |
| BS2 cmdId / EVT layout change | `tbs-core` major |
| BLE session behavior break | `tbs-ble-session` major |

Add-ons declare `apiVersion` in `defineTbsAddon`. Bootstrap rejects mismatches.

---

## 11. Future transports

`onSample` and UI slots are **transport-neutral**. When `@ternion/tbs-serial-session` or `@ternion/tbs-mqtt-client` ship, the same add-on package works if it only uses:

- `protocol(registry)`
- `session.hooks.onSample`
- `ui(registry)`

Add-ons that call BLE-only helpers must document `peerDependencies` on `@ternion/tbs-ble-session` only.

---

## 12. Related documents

- [ARCHITECTURE.md](./ARCHITECTURE.md) — layer model
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) — Phase 6 add-on task
- [REQUIREMENTS.md](./REQUIREMENTS.md) — FR-EXT requirements
