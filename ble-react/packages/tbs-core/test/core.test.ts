import { describe, expect, it } from "vitest";
import {
  Bs2BleChunkReassembler,
  crc16Ccitt,
  encodeBs2BleChunks,
  encodeBsReq,
  mapSensorSample,
  tryParseBs2Frame,
  tryParseBs2Res,
  tryParseEvtSensor,
  BS_CMD_PING,
  BS_TYPE_EVT_SENSOR,
  SENSOR_SHT40,
} from "../src/index.js";

describe("crc16Ccitt", () => {
  it("is stable for empty", () => {
    expect(crc16Ccitt(new Uint8Array())).toBe(0xffff);
  });
});

describe("encodeBsReq / parse", () => {
  it("round-trips PING frame CRC", () => {
    const wire = encodeBsReq(1, BS_CMD_PING);
    const parsed = tryParseBs2Frame(wire);
    expect(parsed).not.toBeNull();
    expect(parsed!.msgType).toBe(0x02);
    expect(parsed!.payload[2]).toBe(BS_CMD_PING);
  });
});

describe("chunk reassembler", () => {
  it("reassembles multi-chunk frame", () => {
    const frame = encodeBsReq(7, BS_CMD_PING);
    const chunks = encodeBs2BleChunks(frame, 23, 42);
    expect(chunks.length).toBeGreaterThanOrEqual(1);
    const re = new Bs2BleChunkReassembler();
    let out: Uint8Array | null = null;
    for (const c of chunks) {
      out = re.feed(c);
    }
    expect(out).not.toBeNull();
    expect([...out!]).toEqual([...frame]);
  });
});

describe("EVT_SENSOR decode", () => {
  it("maps SHT40 sample", () => {
    // Build a minimal EVT_SENSOR: type 0x04, payload = sid,mask,counter,deviceMs,values
    const values = new Uint8Array(4);
    const v = new DataView(values.buffer);
    v.setInt16(0, 2500, true); // 25.00 C
    v.setInt16(2, 4000, true); // 40.00 %
    const payload = new Uint8Array(10 + values.byteLength);
    payload[0] = SENSOR_SHT40;
    payload[1] = 0x03;
    const pv = new DataView(payload.buffer);
    pv.setUint32(2, 99, true);
    pv.setUint32(6, 1000, true);
    payload.set(values, 10);

    const plen = payload.byteLength;
    const wire = new Uint8Array(3 + 2 + 1 + plen + 2 + 2);
    wire[0] = 0x42;
    wire[1] = 0x53;
    wire[2] = 0x20;
    wire[3] = plen & 0xff;
    wire[4] = (plen >> 8) & 0xff;
    wire[5] = BS_TYPE_EVT_SENSOR;
    wire.set(payload, 6);
    const crc = crc16Ccitt(wire.subarray(3, 6 + plen));
    wire[6 + plen] = crc & 0xff;
    wire[7 + plen] = (crc >> 8) & 0xff;
    wire[8 + plen] = 0x0d;
    wire[9 + plen] = 0x0a;

    const evt = tryParseEvtSensor(wire);
    expect(evt).not.toBeNull();
    const sample = mapSensorSample(evt!);
    expect(sample).not.toBeNull();
    expect(sample!.label).toBe("SHT40");
    expect(sample!.fields.temperatureC).toBe(25);
    expect(sample!.fields.humidityPct).toBe(40);
  });
});

describe("tryParseBs2Res", () => {
  it("returns null for REQ", () => {
    const wire = encodeBsReq(1, BS_CMD_PING);
    expect(tryParseBs2Res(wire)).toBeNull();
  });
});
