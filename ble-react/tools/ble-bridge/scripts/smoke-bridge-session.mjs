/**
 * One-shot smoke: host BLE bridge → connect → notify → PING → count EVT frames.
 * Mirrors dashboard Host-bridge path (no Chrome Web Bluetooth).
 */
import WebSocket from "ws";

const URL = process.env.TBS_BLE_BRIDGE_URL ?? "ws://127.0.0.1:9788";
const PING_WIRE = Buffer.from("425320040002010001000e310d0a", "hex");
const BS2_BLE_CHUNK_VER = 1;
const BS2_BLE_CHUNK_FLAG_EOR = 0x01;
const BS2_BLE_CHUNK_HEADER_LEN = 6;
const BS_TYPE_RES = 0x03;
const BS_TYPE_EVT = 0x04;
const BS_CMD_PING = 0x01;

class Reassembler {
  constructor() {
    this.pending = [];
    this.expectedTotal = 0;
    this.activeSeq = -1;
  }
  reset() {
    this.pending = [];
    this.expectedTotal = 0;
    this.activeSeq = -1;
  }
  feed(chunk) {
    if (chunk.length < BS2_BLE_CHUNK_HEADER_LEN || chunk[0] !== BS2_BLE_CHUNK_VER) {
      this.reset();
      return null;
    }
    const seq = chunk[2] | (chunk[3] << 8);
    const idx = chunk[4];
    const total = chunk[5];
    const payload = chunk.subarray(BS2_BLE_CHUNK_HEADER_LEN);
    if (total < 1 || idx >= total) {
      this.reset();
      return null;
    }
    if (seq !== this.activeSeq || total !== this.expectedTotal) {
      this.pending = Array(total).fill(null);
      this.activeSeq = seq;
      this.expectedTotal = total;
    }
    this.pending[idx] = payload;
    if ((chunk[1] & BS2_BLE_CHUNK_FLAG_EOR) === 0) return null;
    if (this.pending.some((p) => p == null)) {
      this.reset();
      return null;
    }
    const frame = Buffer.concat(this.pending);
    this.reset();
    return frame;
  }
}

function tryType(frame) {
  if (frame.length < 6 || frame[0] !== 0x42 || frame[1] !== 0x53 || frame[2] !== 0x20) return null;
  return frame[5];
}

function tryPingRes(frame) {
  if (tryType(frame) !== BS_TYPE_RES || frame.length < 14) return null;
  const plen = frame[3] | (frame[4] << 8);
  const body = frame.subarray(6, 6 + plen);
  if (body.length < 4) return null;
  const cmdId = body[2];
  const status = body[3];
  if (cmdId !== BS_CMD_PING || status !== 0) return null;
  return { reqId: body[0] | (body[1] << 8), status };
}

function waitMsg(ws, match, timeoutMs = 45000) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => {
      ws.off("message", onMsg);
      reject(new Error(`timeout waiting ${timeoutMs}ms`));
    }, timeoutMs);
    function onMsg(data) {
      let msg;
      try {
        msg = JSON.parse(String(data));
      } catch {
        return;
      }
      if (msg.type === "error") {
        clearTimeout(t);
        ws.off("message", onMsg);
        reject(new Error(msg.message ?? "bridge error"));
        return;
      }
      if (match(msg)) {
        clearTimeout(t);
        ws.off("message", onMsg);
        resolve(msg);
      }
    }
    ws.on("message", onMsg);
  });
}

async function main() {
  const ws = new WebSocket(URL);
  await new Promise((res, rej) => {
    ws.once("open", res);
    ws.once("error", rej);
  });
  console.log("WS open", URL);

  await waitMsg(ws, (m) => m.type === "hello", 5000);
  console.log("hello ok");

  ws.send(JSON.stringify({ type: "connect" }));
  const connected = await waitMsg(ws, (m) => m.type === "connected", 60000);
  console.log(`connected: ${connected.name} (${connected.address}) chars=${(connected.chars ?? []).length}`);

  const reassembler = new Reassembler();
  let raw = 0;
  let evt = 0;
  let pingRes = 0;
  const frames = [];

  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(String(data));
    } catch {
      return;
    }
    if (msg.type !== "notify" || !msg.data) return;
    raw += 1;
    const chunk = Buffer.from(msg.data, "base64");
    let frame = null;
    if (chunk.length >= 3 && chunk[0] === 0x42 && chunk[1] === 0x53 && chunk[2] === 0x20) {
      reassembler.reset();
      frame = chunk;
    } else if (chunk[0] === BS2_BLE_CHUNK_VER) {
      frame = reassembler.feed(chunk);
    }
    if (!frame) return;
    frames.push(frame);
    const t = tryType(frame);
    if (t === BS_TYPE_EVT) evt += 1;
    if (tryPingRes(frame)) pingRes += 1;
  });

  ws.send(JSON.stringify({ type: "start_notify" }));
  await waitMsg(ws, (m) => m.type === "notify_started", 15000);
  console.log("notify started");
  await new Promise((r) => setTimeout(r, 400));

  // Write PING immediately (post-CCCD quiet window)
  ws.send(
    JSON.stringify({
      type: "write_rx",
      data: PING_WIRE.toString("base64"),
      withResponse: false,
    }),
  );
  await waitMsg(ws, (m) => m.type === "write_ok", 10000);
  console.log("PING write_ok");

  const deadline = Date.now() + 8000;
  while (Date.now() < deadline && pingRes < 1) {
    await new Promise((r) => setTimeout(r, 100));
  }
  console.log(`after PING window: notifies=${raw} frames=${frames.length} pingRes=${pingRes} evt=${evt}`);

  // Soak EVT briefly
  const t0 = Date.now();
  const evt0 = evt;
  await new Promise((r) => setTimeout(r, 5000));
  const elapsed = (Date.now() - t0) / 1000;
  const dEvt = evt - evt0;
  const hz = dEvt / elapsed;
  console.log(`soak 5s: +EVT=${dEvt} rate=${hz.toFixed(1)} Hz total_notifies=${raw}`);

  ws.send(JSON.stringify({ type: "disconnect" }));
  await new Promise((r) => setTimeout(r, 300));
  ws.close();

  if (pingRes < 1) {
    console.error("FAIL: no PING RES");
    process.exit(4);
  }
  if (dEvt < 1) {
    console.error("FAIL: no EVT_SENSOR during soak (set POLICY 0x07 / CCCD TX_EVT)");
    process.exit(3);
  }
  console.log(`PASS: bridge connect + PING + EVT ${hz.toFixed(1)} Hz`);
  process.exit(0);
}

main().catch((e) => {
  console.error("FAIL:", e.message || e);
  process.exit(1);
});
