/**
 * Host BLE bridge transport — talks to tools/ble-bridge over WebSocket.
 * Implements TbsBleTransport so labs work without Windows browser Web Bluetooth.
 */
import type { TbsBleTransport } from "@ternion/tbs-ble-session";

export const DEFAULT_BLE_BRIDGE_URL = "ws://127.0.0.1:9788";

export type BridgeCharInfo = {
  label: string;
  uuid: string;
  properties: string[];
};

export type HostBleBridgeTransport = TbsBleTransport & {
  listCharacteristics(): BridgeCharInfo[];
  getBridgeUrl(): string;
};

type BridgeMsg = {
  type: string;
  message?: string;
  name?: string;
  address?: string;
  chars?: BridgeCharInfo[];
  data?: string;
  level?: string;
  reason?: string;
};

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function bytesToB64(data: Uint8Array): string {
  let s = "";
  for (let i = 0; i < data.length; i++) s += String.fromCharCode(data[i]!);
  return btoa(s);
}

export function createHostBleBridgeTransport(
  options: {
    url?: string;
    onDisconnected?: () => void;
    onLog?: (level: "info" | "warn" | "error", msg: string) => void;
  } = {},
): HostBleBridgeTransport {
  const url = options.url ?? DEFAULT_BLE_BRIDGE_URL;
  let ws: WebSocket | null = null;
  let connected = false;
  let device = { name: "TESAIoT", address: "" };
  let chars: BridgeCharInfo[] = [];
  let notifyCb: ((chunk: Uint8Array) => void) | null = null;
  let helloWait: { resolve: () => void; reject: (e: Error) => void } | null = null;
  let pending = new Map<
    string,
    { resolve: (v: unknown) => void; reject: (e: Error) => void; match: (m: BridgeMsg) => boolean }
  >();

  const log = (level: "info" | "warn" | "error", msg: string) => {
    options.onLog?.(level, msg);
  };

  const rejectAll = (err: Error) => {
    for (const [, p] of pending) p.reject(err);
    pending.clear();
    if (helloWait) {
      helloWait.reject(err);
      helloWait = null;
    }
  };

  const waitFor = <T,>(
    key: string,
    match: (m: BridgeMsg) => boolean,
    timeoutMs = 45_000,
  ): Promise<T> => {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => {
        pending.delete(key);
        reject(new Error(`bridge timeout waiting for ${key} (${timeoutMs} ms)`));
      }, timeoutMs);
      pending.set(key, {
        match,
        resolve: (v) => {
          window.clearTimeout(timer);
          resolve(v as T);
        },
        reject: (e) => {
          window.clearTimeout(timer);
          reject(e);
        },
      });
    });
  };

  const send = (msg: object) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error(`BLE bridge not connected (${url}). Run: npm start in tools/ble-bridge`);
    }
    ws.send(JSON.stringify(msg));
  };

  const ensureSocket = (): Promise<void> => {
    if (ws && ws.readyState === WebSocket.OPEN) return Promise.resolve();
    return new Promise((resolve, reject) => {
      try {
        ws = new WebSocket(url);
      } catch (e) {
        reject(
          new Error(
            `Cannot open ${url}. Start the Node bridge: cd tools/ble-bridge && npm start`,
          ),
        );
        return;
      }
      const timer = window.setTimeout(() => {
        reject(
          new Error(
            `No hello from bridge at ${url}. Is it running? cd tools/ble-bridge && npm start`,
          ),
        );
      }, 5000);
      helloWait = {
        resolve: () => {
          window.clearTimeout(timer);
          helloWait = null;
          resolve();
        },
        reject: (e) => {
          window.clearTimeout(timer);
          helloWait = null;
          reject(e);
        },
      };
      ws.onopen = () => {
        log("info", `WS open ${url}`);
      };
      ws.onerror = () => {
        const err = new Error(
          `WebSocket error to ${url}. Start bridge: cd tools/ble-bridge && npm start`,
        );
        if (helloWait) helloWait.reject(err);
        rejectAll(err);
      };
      ws.onclose = () => {
        const was = connected;
        connected = false;
        ws = null;
        rejectAll(new Error("BLE bridge WebSocket closed"));
        if (was) options.onDisconnected?.();
      };
      ws.onmessage = (ev) => {
        let msg: BridgeMsg;
        try {
          msg = JSON.parse(String(ev.data)) as BridgeMsg;
        } catch {
          return;
        }
        if (msg.type === "hello") {
          helloWait?.resolve();
          return;
        }
        if (msg.type === "log" && msg.message) {
          const level =
            msg.level === "error" || msg.level === "warn" ? msg.level : "info";
          log(level, `[bridge] ${msg.message}`);
          return;
        }
        if (msg.type === "disconnected") {
          connected = false;
          for (const [key, p] of [...pending]) {
            if (key.startsWith("connect") || p.match(msg)) {
              pending.delete(key);
              p.reject(new Error(msg.reason ?? "disconnected"));
            }
          }
          options.onDisconnected?.();
          return;
        }
        if (msg.type === "error") {
          const err = new Error(msg.message ?? "bridge error");
          for (const [key, p] of [...pending]) {
            pending.delete(key);
            p.reject(err);
          }
          return;
        }
        for (const [key, p] of [...pending]) {
          if (p.match(msg)) {
            pending.delete(key);
            p.resolve(msg);
            return;
          }
        }
        if (msg.type === "notify" && msg.data && notifyCb) {
          notifyCb(b64ToBytes(msg.data));
        }
      };
    });
  };

  return {
    getBridgeUrl() {
      return url;
    },

    listCharacteristics() {
      return chars;
    },

    async connect() {
      await ensureSocket();
      const done = waitFor<BridgeMsg>("connect", (m) => m.type === "connected", 60_000);
      send({ type: "connect" });
      const msg = await done;
      connected = true;
      device = {
        name: msg.name ?? "TESAIoT",
        address: msg.address ?? "",
      };
      chars = msg.chars ?? [];
      return { ...device };
    },

    async disconnect() {
      notifyCb = null;
      try {
        if (ws && ws.readyState === WebSocket.OPEN) {
          const done = waitFor("disconnect", (m) => m.type === "disconnected", 8_000).catch(
            () => null,
          );
          send({ type: "disconnect" });
          await done;
        }
      } catch {
        /* ignore */
      }
      connected = false;
      try {
        ws?.close();
      } catch {
        /* ignore */
      }
      ws = null;
    },

    async startNotify(onChunk) {
      notifyCb = onChunk;
      await ensureSocket();
      const done = waitFor("start_notify", (m) => m.type === "notify_started", 15_000);
      send({ type: "start_notify" });
      await done;
    },

    async stopNotify() {
      notifyCb = null;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      try {
        const done = waitFor("stop_notify", (m) => m.type === "notify_stopped", 8_000);
        send({ type: "stop_notify" });
        await done;
      } catch {
        /* ignore */
      }
    },

    async writeRx(data, withResponse = false) {
      await ensureSocket();
      const done = waitFor("write_rx", (m) => m.type === "write_ok", 15_000);
      send({ type: "write_rx", data: bytesToB64(data), withResponse });
      await done;
    },

    async readLink() {
      await ensureSocket();
      const done = waitFor<BridgeMsg>("read_link", (m) => m.type === "link", 15_000);
      send({ type: "read_link" });
      const msg = await done;
      if (!msg.data) throw new Error("empty link payload");
      return b64ToBytes(msg.data);
    },

    isConnected() {
      return connected && Boolean(ws && ws.readyState === WebSocket.OPEN);
    },
  };
}
