import type { LinkSnapshot, SensorSample } from "@ternion/tbs-core";

/** GATT-level BLE transport — Web Bluetooth adapter implements this. */
export interface TbsBleTransport {
  connect(): Promise<{ name: string; address: string }>;
  disconnect(): Promise<void>;
  /** Enable BS_TX notifications; callback receives raw ATT payloads. */
  startNotify(onChunk: (chunk: Uint8Array) => void): Promise<void>;
  stopNotify(): Promise<void>;
  /** Write BS_RX (Write Command by default). */
  writeRx(data: Uint8Array, withResponse?: boolean): Promise<void>;
  readLink(): Promise<Uint8Array>;
  isConnected(): boolean;
}

export type ConnPhase = "idle" | "connecting" | "linked" | "live" | "error";

export type SessionEvents = {
  onPhase?: (phase: ConnPhase) => void;
  onSample?: (sample: SensorSample) => void;
  onLink?: (snap: LinkSnapshot) => void;
  onLog?: (level: "info" | "warn" | "error", msg: string) => void;
  onRawNotify?: (chunk: Uint8Array) => void;
};
