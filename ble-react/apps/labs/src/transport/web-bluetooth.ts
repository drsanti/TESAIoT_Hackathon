/**
 * Web Bluetooth adapter — ONLY file that may call navigator.bluetooth.
 *
 * Lab 01–02 (secure context + requestDevice) can succeed while Lab 03+ fails:
 * the Windows Chrome failure mode is almost always gatt.connect / GATT discovery.
 */
import {
  BS2_BLE_ADV_NAME_PREFIX,
  BS2_BLE_CHAR_BS_LINK_UUID,
  BS2_BLE_CHAR_BS_RX_UUID,
  BS2_BLE_CHAR_BS_TX_UUID,
  BS2_BLE_SERVICE_UUID,
} from "@ternion/tbs-core";
import type { TbsBleTransport } from "@ternion/tbs-ble-session";

export type WebBluetoothSupport = {
  supported: boolean;
  secureContext: boolean;
  reason?: string;
};

export type CharInfo = {
  label: string;
  uuid: string;
  properties: string[];
};

export function detectWebBluetoothSupport(): WebBluetoothSupport {
  const secureContext = typeof window !== "undefined" && window.isSecureContext;
  const hasApi =
    typeof navigator !== "undefined" &&
    "bluetooth" in navigator &&
    typeof (navigator as Navigator & { bluetooth?: Bluetooth }).bluetooth?.requestDevice ===
      "function";

  if (!secureContext) {
    return {
      supported: false,
      secureContext: false,
      reason: "Web Bluetooth needs a secure context (http://localhost or https://).",
    };
  }
  if (!hasApi) {
    return {
      supported: false,
      secureContext: true,
      reason: "Web Bluetooth is unavailable. Use Chrome or Edge (not Safari/Firefox).",
    };
  }
  return { supported: true, secureContext: true };
}

/** User closed the chooser — not a hard session failure. */
export function isUserCancelledBleError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const name = "name" in err ? String((err as { name?: string }).name) : "";
  const msg = "message" in err ? String((err as { message?: string }).message) : "";
  if (/cancelled|canceled|chooser/i.test(msg)) return true;
  return name === "AbortError";
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function propsOf(c: BluetoothRemoteGATTCharacteristic): string[] {
  const p = c.properties;
  const out: string[] = [];
  if (p.read) out.push("read");
  if (p.write) out.push("write");
  if (p.writeWithoutResponse) out.push("write-without-response");
  if (p.notify) out.push("notify");
  if (p.indicate) out.push("indicate");
  return out;
}

function rawBleMessage(err: unknown): string {
  if (err instanceof Error) return err.message || err.name;
  return String(err);
}

/**
 * Keep a short human hint. Never nest formatBleError on an already-wrapped Error
 * (outer catch used to produce "GATT connect … Raw: GATT discovery … Raw: …").
 */
function formatBleError(err: unknown, step: string): Error {
  if (isUserCancelledBleError(err)) {
    return new Error("Device picker cancelled.");
  }
  const raw = rawBleMessage(err);
  if (
    /WinRT dropped GATT|failed \(Windows Web Bluetooth\)|BS2 GATT service not found/i.test(raw)
  ) {
    return err instanceof Error ? err : new Error(raw);
  }
  if (
    /Connection attempt failed|GATT Server is disconnected|NetworkError|GATT disconnected|Cannot retrieve services|no longer in range/i.test(
      raw,
    )
  ) {
    const root =
      raw.match(
        /Cannot retrieve services[^.]*(?:\.)?|GATT Server is disconnected[^.]*(?:\.)?|Connection attempt failed[^.]*(?:\.)?|no longer in range[^.]*(?:\.)?/i,
      )?.[0]?.trim() ?? raw;
    return new Error(
      `${step}: WinRT dropped GATT (${root}). Soft-blue RESET + pair TESAIoT-* in Windows Settings, or use labs → Host bridge (Node).`,
    );
  }
  if (/No Services found|NotFoundError/i.test(raw)) {
    return new Error(
      `${step}: BS2 GATT service not found (${BS2_BLE_SERVICE_UUID}). Raw: ${raw}`,
    );
  }
  const name = err instanceof Error ? err.name : "Error";
  return new Error(`${step}: ${name}: ${raw}`);
}

function uuidEq(a: string, b: string): boolean {
  return a.replace(/-/g, "").toLowerCase() === b.replace(/-/g, "").toLowerCase();
}

export type WebBluetoothTransport = TbsBleTransport & {
  listCharacteristics(): CharInfo[];
};

export function createWebBluetoothTransport(
  options: { onDisconnected?: () => void } = {},
): WebBluetoothTransport {
  let device: BluetoothDevice | null = null;
  let server: BluetoothRemoteGATTServer | null = null;
  let rx: BluetoothRemoteGATTCharacteristic | null = null;
  let tx: BluetoothRemoteGATTCharacteristic | null = null;
  let link: BluetoothRemoteGATTCharacteristic | null = null;
  let notifyHandler: ((ev: Event) => void) | null = null;
  let charInfos: CharInfo[] = [];
  let gattserverHandler: ((ev: Event) => void) | null = null;
  /** Suppress disconnect callbacks while connect() is still in flight. */
  let connectInFlight = false;

  const clearChars = () => {
    rx = null;
    tx = null;
    link = null;
    charInfos = [];
  };

  const detachDeviceListeners = () => {
    if (device && gattserverHandler) {
      device.removeEventListener("gattserverdisconnected", gattserverHandler);
    }
    gattserverHandler = null;
  };

  const hardCleanup = async () => {
    try {
      if (tx && notifyHandler) {
        tx.removeEventListener("characteristicvaluechanged", notifyHandler);
        try {
          await tx.stopNotifications();
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore */
    }
    notifyHandler = null;
    detachDeviceListeners();
    try {
      if (server?.connected) server.disconnect();
      else if (device?.gatt?.connected) device.gatt.disconnect();
    } catch {
      /* ignore */
    }
    server = null;
    device = null;
    clearChars();
  };

  /**
   * Always use a fresh chooser scan.
   * TESAIoT uses a rotating random address — navigator.bluetooth.getDevices()
   * often returns a stale grant and gatt.connect() then fails with
   * "Bluetooth Device is no longer in range" (Lab 02 picker still works).
   */
  const pickDevice = async (): Promise<BluetoothDevice> => {
    // Prefer acceptAll on Windows: combining namePrefix+services in ONE filter
    // object has caused connect-then-drop (~10-100 ms) on this kit's WinRT path.
    try {
      return await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: [BS2_BLE_SERVICE_UUID],
      });
    } catch (e) {
      if (isUserCancelledBleError(e)) throw e;
      return navigator.bluetooth.requestDevice({
        filters: [
          { namePrefix: BS2_BLE_ADV_NAME_PREFIX },
          { services: [BS2_BLE_SERVICE_UUID] },
        ],
        optionalServices: [BS2_BLE_SERVICE_UUID],
      });
    }
  };

  const discover = async (gattServer: BluetoothRemoteGATTServer) => {
    if (!gattServer.connected) {
      throw new Error("GATT server disconnected before service discovery");
    }

    let service: BluetoothRemoteGATTService | undefined;
    try {
      try {
        await gattServer.getPrimaryServices();
      } catch {
        /* optional full enum */
      }
      service = await gattServer.getPrimaryService(BS2_BLE_SERVICE_UUID);
    } catch (e) {
      const msg = rawBleMessage(e);
      // Only enumerate-all when the UUID lookup misses — not on link-drop NetworkError.
      if (!/NotFoundError|no services|not found/i.test(msg)) {
        throw e;
      }
      const all = await gattServer.getPrimaryServices();
      service = all.find((s) => uuidEq(s.uuid, BS2_BLE_SERVICE_UUID));
      if (!service) {
        throw new Error(
          `BS2 service missing after full enum (${all.length} services). Raw: ${msg}`,
        );
      }
    }

    rx = await service.getCharacteristic(BS2_BLE_CHAR_BS_RX_UUID);
    tx = await service.getCharacteristic(BS2_BLE_CHAR_BS_TX_UUID);
    link = await service.getCharacteristic(BS2_BLE_CHAR_BS_LINK_UUID);

    charInfos = [
      { label: "BS_RX", uuid: BS2_BLE_CHAR_BS_RX_UUID, properties: propsOf(rx) },
      { label: "BS_TX", uuid: BS2_BLE_CHAR_BS_TX_UUID, properties: propsOf(tx) },
      { label: "BS_LINK", uuid: BS2_BLE_CHAR_BS_LINK_UUID, properties: propsOf(link) },
    ];
  };

  const waitForBs2Gatt = async (gattServer: BluetoothRemoteGATTServer) => {
    let lastErr: unknown;
    for (let i = 0; i < 5; i++) {
      if (!device?.gatt?.connected) {
        throw new Error(
          i === 0
            ? "GATT disconnected before service discovery"
            : "GATT disconnected while waiting for BS2 services",
        );
      }
      try {
        await discover(gattServer);
        server = gattServer;
        return;
      } catch (e) {
        lastErr = e;
        const msg = rawBleMessage(e);
        if (/disconnected|NetworkError|Connection attempt failed/i.test(msg)) {
          throw e instanceof Error ? e : new Error(msg);
        }
        await sleep(200);
      }
    }
    throw formatBleError(lastErr ?? new Error("timeout"), "Discover BS2 service");
  };

  return {
    async connect() {
      const support = detectWebBluetoothSupport();
      if (!support.supported) {
        throw new Error(support.reason ?? "Web Bluetooth unavailable");
      }

      await hardCleanup();
      connectInFlight = true;

      try {
        try {
          device = await pickDevice();
        } catch (e) {
          throw formatBleError(e, "Request device");
        }

        if (!device.gatt) {
          throw new Error("Device has no GATT server (device.gatt is null)");
        }

        gattserverHandler = () => {
          clearChars();
          server = null;
          if (!connectInFlight) {
            options.onDisconnected?.();
          }
        };
        device.addEventListener("gattserverdisconnected", gattserverHandler);

        // One attempt only — WinRT ADV often dies after disconnect+reconnect hammers.
        try {
          if (!device.gatt.connected) {
            await device.gatt.connect();
          }
        } catch (e) {
          throw formatBleError(e, "GATT connect");
        }

        if (!device.gatt?.connected) {
          throw new Error("GATT connect resolved but connected=false");
        }

        // Do NOT idle after connect on Windows — the link often drops during a
        // "settle" sleep ("disconnected during settle"). Discover immediately.
        try {
          await waitForBs2Gatt(device.gatt);
        } catch (e) {
          throw formatBleError(e, "GATT discovery");
        }

        connectInFlight = false;
        return {
          name: device.name ?? "TESAIoT",
          address: device.id,
        };
      } catch (e) {
        clearChars();
        server = null;
        try {
          if (device?.gatt?.connected) device.gatt.disconnect();
        } catch {
          /* ignore */
        }
        detachDeviceListeners();
        device = null;
        // Re-throw already-formatted errors from request/connect/discovery.
        throw formatBleError(e, "GATT connect");
      } finally {
        connectInFlight = false;
      }
    },

    async disconnect() {
      connectInFlight = false;
      await hardCleanup();
    },

    async startNotify(onChunk) {
      if (!tx) throw new Error("not connected");
      notifyHandler = (ev: Event) => {
        const target = ev.target as BluetoothRemoteGATTCharacteristic;
        const value = target.value;
        if (!value) return;
        onChunk(new Uint8Array(value.buffer, value.byteOffset, value.byteLength));
      };
      tx.addEventListener("characteristicvaluechanged", notifyHandler);
      await tx.startNotifications();
    },

    async stopNotify() {
      if (!tx) return;
      if (notifyHandler) {
        tx.removeEventListener("characteristicvaluechanged", notifyHandler);
        notifyHandler = null;
      }
      try {
        await tx.stopNotifications();
      } catch {
        /* ignore */
      }
    },

    async writeRx(data, withResponse = false) {
      if (!rx) throw new Error("not connected");
      const buffer = data.buffer.slice(
        data.byteOffset,
        data.byteOffset + data.byteLength,
      ) as ArrayBuffer;
      if (withResponse) {
        await rx.writeValueWithResponse(buffer);
      } else {
        await rx.writeValueWithoutResponse(buffer);
      }
    },

    async readLink() {
      if (!link) throw new Error("not connected");
      const value = await link.readValue();
      return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    },

    isConnected() {
      return Boolean(server?.connected || device?.gatt?.connected);
    },

    listCharacteristics() {
      return charInfos;
    },
  };
}
