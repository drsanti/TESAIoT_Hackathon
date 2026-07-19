/** BS_LINK characteristic snapshot */

export type LinkSnapshot = {
  state: number;
  mtu: number;
  txDrops: number;
  raw: Uint8Array;
};

export function decodeLinkSnapshot(raw: Uint8Array): LinkSnapshot {
  const state = raw.byteLength > 0 ? raw[0]! : 0;
  const mtu = raw.byteLength >= 3 ? raw[1]! | (raw[2]! << 8) : 0;
  let txDrops = 0;
  if (raw.byteLength >= 7) {
    txDrops = raw[3]! | (raw[4]! << 8) | (raw[5]! << 16) | (raw[6]! << 24);
  }
  return { state, mtu, txDrops, raw: new Uint8Array(raw) };
}

export function formatLinkSnapshot(snap: LinkSnapshot): string {
  const hex = Array.from(snap.raw)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `state=${snap.state} mtu=${snap.mtu} tx_drops=${snap.txDrops} raw=${hex || "(empty)"}`;
}

/** Teaching hint when firmware has not published a negotiated ATT MTU yet. */
export function linkMtuHint(snap: LinkSnapshot): string | null {
  if (snap.state === 1 && snap.mtu === 0) {
    return "mtu=0: snapshot not updated by MTU exchange yet (ATT default is often 23). Click Re-read BS_LINK after a second.";
  }
  return null;
}
