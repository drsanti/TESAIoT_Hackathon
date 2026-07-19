/** Locked BS2 GATT IDs (must match tbs-core / firmware). */
export const SERVICE = "6f6b7a80-0001-4000-8000-00805f9b34fb";
export const BS_RX = "6f6b7a80-0001-4001-8000-00805f9b34fb";
export const BS_TX = "6f6b7a80-0001-4002-8000-00805f9b34fb";
export const BS_LINK = "6f6b7a80-0001-4003-8000-00805f9b34fb";
export const NAME_PREFIX = "TESAIoT-";

export function uuidEq(a, b) {
  return String(a).replace(/-/g, "").toLowerCase() === String(b).replace(/-/g, "").toLowerCase();
}

export function b64FromBytes(u8) {
  return Buffer.from(u8).toString("base64");
}

export function bytesFromB64(b64) {
  return new Uint8Array(Buffer.from(String(b64), "base64"));
}
