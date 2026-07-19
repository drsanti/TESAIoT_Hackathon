import { describe, expect, it } from "vitest";
import {
  BLE_POLICY_FACTORY_STREAMING,
  BS2_BLE_CHUNK_VER,
  BS_CMD_BLE_POLICY_SET,
  BS_CMD_PING,
  BS_TYPE_EVT_SENSOR,
  BS_TYPE_RES,
  crc16Ccitt,
  encodeBs2BleChunks,
  SENSOR_SHT40,
  tryParseBs2Frame,
} from "@ternion/tbs-core";
import { createTbsBleSession } from "../src/index.js";
import type { TbsBleTransport } from "../src/transport.js";

function encodeBsRes(reqId: number, cmdId: number, status: number, body: Uint8Array = new Uint8Array()): Uint8Array {
  const payload = new Uint8Array(4 + body.byteLength);
  payload[0] = reqId & 0xff;
  payload[1] = (reqId >> 8) & 0xff;
  payload[2] = cmdId & 0xff;
  payload[3] = status & 0xff;
  payload.set(body, 4);
  const plen = payload.byteLength;
  const wire = new Uint8Array(3 + 2 + 1 + plen + 2 + 2);
  wire[0] = 0x42;
  wire[1] = 0x53;
  wire[2] = 0x20;
  wire[3] = plen & 0xff;
  wire[4] = (plen >> 8) & 0xff;
  wire[5] = BS_TYPE_RES;
  wire.set(payload, 6);
  const crc = crc16Ccitt(wire.subarray(3, 6 + plen));
  wire[6 + plen] = crc & 0xff;
  wire[7 + plen] = (crc >> 8) & 0xff;
  wire[8 + plen] = 0x0d;
  wire[9 + plen] = 0x0a;
  return wire;
}

function buildSht40Evt(counter = 1): Uint8Array {
  const values = new Uint8Array(4);
  const v = new DataView(values.buffer);
  v.setInt16(0, 2100, true);
  v.setInt16(2, 5500, true);
  const payload = new Uint8Array(10 + values.byteLength);
  payload[0] = SENSOR_SHT40;
  payload[1] = 0x03;
  const pv = new DataView(payload.buffer);
  pv.setUint32(2, counter, true);
  pv.setUint32(6, 500, true);
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
  return wire;
}

function makeEchoTransport(): {
  transport: TbsBleTransport;
  inject: (frame: Uint8Array) => void;
} {
  let onChunk: ((c: Uint8Array) => void) | null = null;
  const transport: TbsBleTransport = {
    async connect() {
      return { name: "TESAIoT-TEST", address: "AA:BB" };
    },
    async disconnect() {},
    async startNotify(cb) {
      onChunk = cb;
    },
    async stopNotify() {
      onChunk = null;
    },
    async writeRx(data) {
      const frame = tryParseBs2Frame(data);
      if (!frame || frame.msgType !== 0x02 || frame.payload.byteLength < 4) return;
      const reqId = frame.payload[0]! | (frame.payload[1]! << 8);
      const cmdId = frame.payload[2]!;
      let body = new Uint8Array();
      if (cmdId === BS_CMD_BLE_POLICY_SET && frame.payload.byteLength >= 5) {
        body = Uint8Array.of(frame.payload[4]!);
      }
      queueMicrotask(() => {
        onChunk?.(encodeBsRes(reqId, cmdId, 0, body));
      });
    },
    async readLink() {
      return new Uint8Array([1, 23, 0]);
    },
    isConnected() {
      return true;
    },
  };
  return {
    transport,
    inject: (frame) => onChunk?.(frame),
  };
}

describe("createTbsBleSession fake transport", () => {
  it("delivers EVT via goLive notify", async () => {
    let onChunk: ((c: Uint8Array) => void) | null = null;
    const samples: number[] = [];

    const transport: TbsBleTransport = {
      async connect() {
        return { name: "TESAIoT-TEST", address: "AA:BB" };
      },
      async disconnect() {},
      async startNotify(cb) {
        onChunk = cb;
      },
      async stopNotify() {
        onChunk = null;
      },
      async writeRx() {},
      async readLink() {
        return new Uint8Array([1, 23, 0]);
      },
      isConnected() {
        return true;
      },
    };

    const session = createTbsBleSession(transport, {
      onSample(s) {
        samples.push(s.sensorId);
      },
    });

    await session.connect();
    await session.goLive(10);
    expect(session.getPhase()).toBe("live");

    onChunk?.(buildSht40Evt(1));
    expect(samples).toEqual([SENSOR_SHT40]);

    samples.length = 0;
    for (const c of encodeBs2BleChunks(buildSht40Evt(2), 64, 9)) onChunk?.(c);
    expect(samples).toEqual([SENSOR_SHT40]);
    expect(encodeBs2BleChunks(buildSht40Evt(2), 64, 9)[0]![0]).toBe(BS2_BLE_CHUNK_VER);

    await session.disconnect();
    expect(session.getPhase()).toBe("idle");
  });

  it("ping and enableStreaming correlate RES", async () => {
    const { transport } = makeEchoTransport();
    const session = createTbsBleSession(transport);
    await session.connect();
    await session.goLive(5);

    const pong = await session.ping({ timeoutMs: 1000, attempts: 1 });
    expect(pong.cmdId).toBe(BS_CMD_PING);
    expect(pong.status).toBe(0);

    await session.enableStreaming({ settleMs: 5, policyTimeoutMs: 1000 });
    expect(session.getPolicyFlags()).toBe(BLE_POLICY_FACTORY_STREAMING);
  });

  it("enableStreaming soft-fails POLICY when EVT already flowing", async () => {
    let onChunk: ((c: Uint8Array) => void) | null = null;
    const transport: TbsBleTransport = {
      async connect() {
        return { name: "TESAIoT-TEST", address: "AA:BB" };
      },
      async disconnect() {},
      async startNotify(cb) {
        onChunk = cb;
      },
      async stopNotify() {
        onChunk = null;
      },
      async writeRx() {
        /* never reply — POLICY times out */
      },
      async readLink() {
        return new Uint8Array([1, 23, 0]);
      },
      isConnected() {
        return true;
      },
    };

    const session = createTbsBleSession(transport);
    await session.connect();
    await session.goLive(5);
    onChunk?.(buildSht40Evt(7));
    await session.enableStreaming({ settleMs: 5, policyTimeoutMs: 80, policyAttempts: 1 });
    expect(session.getPhase()).toBe("live");
    expect(session.getCounts().get(SENSOR_SHT40)).toBe(1);
  });
});
