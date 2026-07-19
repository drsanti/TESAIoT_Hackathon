/** BS2 framed protocol — wire encode/decode */

export const BS_PREFIX = new Uint8Array([0x42, 0x53, 0x20]); // "BS "
export const BS_TYPE_REQ = 0x02;
export const BS_TYPE_RES = 0x03;
export const BS_TYPE_EVT_SENSOR = 0x04;

export function crc16Ccitt(data: Uint8Array, init = 0xffff): number {
  let crc = init;
  for (let i = 0; i < data.byteLength; i++) {
    crc ^= data[i]! << 8;
    for (let b = 0; b < 8; b++) {
      if (crc & 0x8000) {
        crc = ((crc << 1) ^ 0x1021) & 0xffff;
      } else {
        crc = (crc << 1) & 0xffff;
      }
    }
  }
  return crc;
}

export function encodeBsReq(reqId: number, cmdId: number, body: Uint8Array = new Uint8Array(), flags = 0): Uint8Array {
  const payload = new Uint8Array(4 + body.byteLength);
  payload[0] = reqId & 0xff;
  payload[1] = (reqId >> 8) & 0xff;
  payload[2] = cmdId & 0xff;
  payload[3] = flags & 0xff;
  payload.set(body, 4);

  const plen = payload.byteLength;
  const out = new Uint8Array(3 + 2 + 1 + plen + 2 + 2);
  out.set(BS_PREFIX, 0);
  out[3] = plen & 0xff;
  out[4] = (plen >> 8) & 0xff;
  out[5] = BS_TYPE_REQ;
  out.set(payload, 6);

  const crcRegion = out.subarray(3, 6 + plen);
  const crc = crc16Ccitt(crcRegion);
  out[6 + plen] = crc & 0xff;
  out[7 + plen] = (crc >> 8) & 0xff;
  out[8 + plen] = 0x0d;
  out[9 + plen] = 0x0a;
  return out;
}

export function tryParseBs2Frame(wire: Uint8Array): { msgType: number; payload: Uint8Array } | null {
  if (wire.byteLength < 14) return null;
  if (wire[0] !== 0x42 || wire[1] !== 0x53 || wire[2] !== 0x20) return null;
  const plen = wire[3]! | (wire[4]! << 8);
  const needed = 3 + 2 + 1 + plen + 2 + 2;
  if (wire.byteLength < needed) return null;
  if (wire[needed - 2] !== 0x0d || wire[needed - 1] !== 0x0a) return null;
  const crcExpected = wire[6 + plen]! | (wire[7 + plen]! << 8);
  const crcActual = crc16Ccitt(wire.subarray(3, 6 + plen));
  if (crcActual !== crcExpected) return null;
  return { msgType: wire[5]!, payload: wire.subarray(6, 6 + plen) };
}

export function tryParseBs2Res(
  wire: Uint8Array,
): { reqId: number; cmdId: number; status: number; body: Uint8Array } | null {
  const parsed = tryParseBs2Frame(wire);
  if (!parsed || parsed.msgType !== BS_TYPE_RES || parsed.payload.byteLength < 4) return null;
  const p = parsed.payload;
  return {
    reqId: p[0]! | (p[1]! << 8),
    cmdId: p[2]!,
    status: p[3]!,
    body: p.subarray(4),
  };
}

export type EvtSensorRaw = {
  sensorId: number;
  mask: number;
  counter: number;
  deviceMs: number;
  values: Uint8Array;
};

export function tryParseEvtSensor(wire: Uint8Array): EvtSensorRaw | null {
  const parsed = tryParseBs2Frame(wire);
  if (!parsed || parsed.msgType !== BS_TYPE_EVT_SENSOR || parsed.payload.byteLength < 10) return null;
  const p = parsed.payload;
  const view = new DataView(p.buffer, p.byteOffset, p.byteLength);
  return {
    sensorId: p[0]!,
    mask: p[1]!,
    counter: view.getUint32(2, true),
    deviceMs: view.getUint32(6, true),
    values: p.subarray(10),
  };
}

export function looksLikeBsPrefix(data: Uint8Array): boolean {
  return data.byteLength >= 3 && data[0] === 0x42 && data[1] === 0x53 && data[2] === 0x20;
}
