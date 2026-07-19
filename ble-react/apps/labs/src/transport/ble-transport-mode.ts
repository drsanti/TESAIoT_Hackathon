/** Prefer host Node BLE bridge over Windows browser Web Bluetooth. */
export type BleTransportMode = "web" | "bridge";

const STORAGE_KEY = "tbs.ble.transport";

export function readBleTransportMode(): BleTransportMode {
  try {
    const q = new URLSearchParams(window.location.search).get("ble");
    if (q === "bridge" || q === "host") return "bridge";
    if (q === "web" || q === "chrome") return "web";
  } catch {
    /* ignore */
  }
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "bridge" || v === "web") return v;
  } catch {
    /* ignore */
  }
  // Default bridge on Windows — browser Web Bluetooth often drops in ~10–100 ms.
  if (typeof navigator !== "undefined" && /Windows/i.test(navigator.userAgent)) {
    return "bridge";
  }
  return "web";
}

export function writeBleTransportMode(mode: BleTransportMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}
