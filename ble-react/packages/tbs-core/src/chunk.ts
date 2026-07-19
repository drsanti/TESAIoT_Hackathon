/** ATT chunk envelope v1 */

export const BS2_BLE_CHUNK_VER = 1;
export const BS2_BLE_CHUNK_FLAG_EOR = 0x01;
export const BS2_BLE_CHUNK_FLAG_DROP = 0x02;
export const BS2_BLE_CHUNK_HEADER_LEN = 6;

export type Bs2BleChunkHeader = {
  ver: number;
  flags: number;
  seq: number;
  idx: number;
  total: number;
};

export function encodeBs2BleChunks(frame: Uint8Array, mtu: number, seq: number): Uint8Array[] {
  const maxPayload = Math.max(1, mtu - 3 - BS2_BLE_CHUNK_HEADER_LEN);
  const total = Math.max(1, Math.ceil(frame.byteLength / maxPayload));
  const chunks: Uint8Array[] = [];

  for (let idx = 0; idx < total; idx++) {
    const start = idx * maxPayload;
    const end = Math.min(frame.byteLength, start + maxPayload);
    const payload = frame.subarray(start, end);
    const isLast = idx === total - 1;
    const out = new Uint8Array(BS2_BLE_CHUNK_HEADER_LEN + payload.byteLength);
    out[0] = BS2_BLE_CHUNK_VER;
    out[1] = isLast ? BS2_BLE_CHUNK_FLAG_EOR : 0;
    out[2] = seq & 0xff;
    out[3] = (seq >> 8) & 0xff;
    out[4] = idx;
    out[5] = total;
    out.set(payload, BS2_BLE_CHUNK_HEADER_LEN);
    chunks.push(out);
  }

  return chunks;
}

export class Bs2BleChunkReassembler {
  private pending: (Uint8Array | undefined)[] = [];
  private expectedTotal = 0;
  private activeSeq = -1;

  feed(chunk: Uint8Array): Uint8Array | null {
    if (chunk.byteLength < BS2_BLE_CHUNK_HEADER_LEN) {
      return null;
    }
    if (chunk[0] !== BS2_BLE_CHUNK_VER) {
      this.reset();
      return null;
    }

    const seq = chunk[2]! | (chunk[3]! << 8);
    const idx = chunk[4]!;
    const total = chunk[5]!;
    const payload = chunk.subarray(BS2_BLE_CHUNK_HEADER_LEN);

    if (total < 1 || idx >= total) {
      this.reset();
      return null;
    }

    if (seq !== this.activeSeq || total !== this.expectedTotal) {
      this.pending = new Array<Uint8Array | undefined>(total);
      this.activeSeq = seq;
      this.expectedTotal = total;
    }

    this.pending[idx] = payload;

    if (0 === (chunk[1]! & BS2_BLE_CHUNK_FLAG_EOR)) {
      return null;
    }

    for (let i = 0; i < total; i++) {
      if (!this.pending[i]) {
        this.reset();
        return null;
      }
    }

    const totalLen = this.pending.reduce((sum, p) => sum + (p?.byteLength ?? 0), 0);
    const frame = new Uint8Array(totalLen);
    let offset = 0;
    for (let i = 0; i < total; i++) {
      const part = this.pending[i]!;
      frame.set(part, offset);
      offset += part.byteLength;
    }
    this.reset();
    return frame;
  }

  reset(): void {
    this.pending = [];
    this.expectedTotal = 0;
    this.activeSeq = -1;
  }
}

export function decodeBs2BleChunkHeader(chunk: Uint8Array): Bs2BleChunkHeader | null {
  if (chunk.byteLength < BS2_BLE_CHUNK_HEADER_LEN || chunk[0] !== BS2_BLE_CHUNK_VER) {
    return null;
  }
  return {
    ver: chunk[0]!,
    flags: chunk[1]!,
    seq: chunk[2]! | (chunk[3]! << 8),
    idx: chunk[4]!,
    total: chunk[5]!,
  };
}
