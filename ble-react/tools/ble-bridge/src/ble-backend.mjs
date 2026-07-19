/**
 * Host BLE session via thegecko/webbluetooth (SimpleBLE).
 * Same stack as tools/webbluetooth-diag — not Chrome.
 */
import { Bluetooth } from "webbluetooth";
import {
  BS_LINK,
  BS_RX,
  BS_TX,
  NAME_PREFIX,
  SERVICE,
  b64FromBytes,
  bytesFromB64,
  uuidEq,
} from "./uuids.mjs";

const SCAN_MS = 12_000;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function propsOf(c) {
  const p = c.properties ?? {};
  const out = [];
  if (p.read) out.push("read");
  if (p.write) out.push("write");
  if (p.writeWithoutResponse) out.push("write-without-response");
  if (p.notify) out.push("notify");
  if (p.indicate) out.push("indicate");
  return out;
}

export function createWebBluetoothBackend({ onLog, onDisconnected, onNotify }) {
  let device = null;
  let server = null;
  let rx = null;
  let tx = null;
  let link = null;
  let notifyHandler = null;
  let charInfos = [];

  const log = (level, msg) => onLog?.(level, msg);

  const clear = () => {
    rx = null;
    tx = null;
    link = null;
    charInfos = [];
  };

  const detachNotify = async () => {
    if (tx && notifyHandler) {
      try {
        tx.removeEventListener("characteristicvaluechanged", notifyHandler);
      } catch {
        /* ignore */
      }
      notifyHandler = null;
      try {
        await tx.stopNotifications();
      } catch {
        /* ignore */
      }
    }
  };

  const hardCleanup = async () => {
    await detachNotify();
    try {
      if (server?.connected) server.disconnect();
      else if (device?.gatt?.connected) device.gatt.disconnect();
    } catch {
      /* ignore */
    }
    server = null;
    device = null;
    clear();
  };

  const findChar = async (service, wantUuid, label) => {
    for (let attempt = 1; attempt <= 5; attempt++) {
      try {
        // Prefer direct UUID lookup (SimpleBLE enum is flaky on Win).
        const c = await service.getCharacteristic(wantUuid);
        if (c) return c;
      } catch {
        /* retry via list */
      }
      try {
        service.characteristics = undefined;
        const all = await service.getCharacteristics();
        const hit = all.find((c) => uuidEq(String(c.uuid), wantUuid));
        if (hit) return hit;
        log("warn", `${label}: attempt ${attempt} chars=${all.length}`);
      } catch (e) {
        log("warn", `${label}: enum failed attempt ${attempt}: ${e?.message ?? e}`);
      }
      await sleep(250 * attempt);
    }
    throw new Error(`${label} characteristic not found (${wantUuid})`);
  };

  return {
    async connect() {
      await hardCleanup();

      const bluetooth = new Bluetooth({
        scanTime: SCAN_MS,
        deviceFound: (dev) => {
          const name = dev.name || "";
          if (name.startsWith(NAME_PREFIX) || name === "TESAIoT-") {
            log("info", `scan hit ${name || "(unnamed)"} id=${dev.id}`);
            return true;
          }
          return false;
        },
      });

      log("info", "scanning for TESAIoT-* …");
      device = await bluetooth.requestDevice({
        filters: [{ namePrefix: NAME_PREFIX }, { services: [SERVICE] }],
        optionalServices: [SERVICE],
      });

      device.addEventListener("gattserverdisconnected", () => {
        clear();
        server = null;
        onDisconnected?.("gattserverdisconnected");
      });

      if (!device.gatt) throw new Error("device.gatt is null");
      server = await device.gatt.connect();
      log("info", `GATT connected name=${device.name ?? "?"} id=${device.id}`);

      try {
        await server.getPrimaryServices();
      } catch {
        /* optional */
      }
      const service = await server.getPrimaryService(SERVICE);

      rx = await findChar(service, BS_RX, "BS_RX");
      tx = await findChar(service, BS_TX, "BS_TX");
      link = await findChar(service, BS_LINK, "BS_LINK");

      charInfos = [
        { label: "BS_RX", uuid: BS_RX, properties: propsOf(rx) },
        { label: "BS_TX", uuid: BS_TX, properties: propsOf(tx) },
        { label: "BS_LINK", uuid: BS_LINK, properties: propsOf(link) },
      ];

      return {
        name: device.name ?? "TESAIoT",
        address: String(device.id ?? ""),
        chars: charInfos,
      };
    },

    async disconnect() {
      await hardCleanup();
    },

    isConnected() {
      return Boolean(server?.connected || device?.gatt?.connected);
    },

    async startNotify() {
      if (!tx) throw new Error("not connected");
      await detachNotify();
      notifyHandler = (ev) => {
        const target = ev.target;
        const value = target?.value;
        if (!value) return;
        const u8 = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
        onNotify?.(u8);
      };
      tx.addEventListener("characteristicvaluechanged", notifyHandler);
      await tx.startNotifications();
    },

    async stopNotify() {
      await detachNotify();
    },

    async writeRx(dataB64, withResponse = false) {
      if (!rx) throw new Error("not connected");
      const data = bytesFromB64(dataB64);
      const buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
      if (withResponse) {
        await rx.writeValueWithResponse(buffer);
      } else {
        await rx.writeValueWithoutResponse(buffer);
      }
    },

    async readLink() {
      if (!link) throw new Error("not connected");
      const value = await link.readValue();
      const u8 = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
      return b64FromBytes(u8);
    },
  };
}
