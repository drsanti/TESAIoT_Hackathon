import {
  BLE_POLICY_FACTORY_STREAMING,
  BS2_BLE_CHUNK_VER,
  BS_CMD_BLE_POLICY_SET,
  BS_CMD_PING,
  BS_CMD_SENSOR_CFG_SET,
  Bs2BleChunkReassembler,
  decodeLinkSnapshot,
  encodeBsReq,
  encodeSensorCfgBody,
  looksLikeBsPrefix,
  mapSensorSample,
  tryParseBs2Res,
  tryParseEvtSensor,
  type SensorCfg,
  type SensorSample,
} from "@ternion/tbs-core";
import type { ConnPhase, SessionEvents, TbsBleTransport } from "./transport.js";

export type Bs2Res = {
  reqId: number;
  cmdId: number;
  status: number;
  body: Uint8Array;
};

export type TbsBleSession = {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  /** EVT-first: enable BS_TX notify (firmware arms TX_EVT on CCCD). */
  goLive(settleMs?: number): Promise<void>;
  /**
   * Notify + POLICY_SET 0x07 heal (ble-flet parity). Soft-fails POLICY wait when
   * EVTs are already flowing or TX_EVT bit is set.
   */
  enableStreaming(opts?: {
    settleMs?: number;
    policyTimeoutMs?: number;
    policyAttempts?: number;
  }): Promise<void>;
  /** Wait for BS2 RES (status 0). Writes during/after notify settle. */
  ping(opts?: { timeoutMs?: number; attempts?: number }): Promise<Bs2Res>;
  setBlePolicy(
    flags: number,
    opts?: { timeoutMs?: number; attempts?: number },
  ): Promise<number>;
  /** Correlated REQ/RES — prefer writeReqFire for teaching fire-and-forget. */
  request(
    cmdId: number,
    body?: Uint8Array,
    opts?: { timeoutMs?: number },
  ): Promise<Bs2Res>;
  applyCfgsFire(cfgs: SensorCfg[], gapMs?: number): Promise<void>;
  writeReqFire(cmdId: number, body?: Uint8Array): Promise<void>;
  readLink(): Promise<ReturnType<typeof decodeLinkSnapshot>>;
  getPhase(): ConnPhase;
  getDevice(): { name: string; address: string } | null;
  getLatest(): Map<number, SensorSample>;
  getCounts(): Map<number, number>;
  getPolicyFlags(): number;
};

type PendingReq = {
  cmdId: number;
  resolve: (res: Bs2Res) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout>;
};

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function createTbsBleSession(
  transport: TbsBleTransport,
  events: SessionEvents = {},
): TbsBleSession {
  let phase: ConnPhase = "idle";
  let device: { name: string; address: string } | null = null;
  let nextReqId = 1;
  let policyFlags = 0;
  let evtRawCount = 0;
  const reassembler = new Bs2BleChunkReassembler();
  const latest = new Map<number, SensorSample>();
  const counts = new Map<number, number>();
  const seen = new Map<number, Set<number>>();
  const pending = new Map<number, PendingReq>();
  let notifyOn = false;

  const setPhase = (p: ConnPhase) => {
    phase = p;
    events.onPhase?.(p);
  };

  const log = (level: "info" | "warn" | "error", msg: string) => {
    events.onLog?.(level, msg);
  };

  const rejectAllPending = (reason: string) => {
    for (const [id, p] of pending) {
      clearTimeout(p.timer);
      p.reject(new Error(reason));
      pending.delete(id);
    }
  };

  const handleFrame = (frame: Uint8Array) => {
    const res = tryParseBs2Res(frame);
    if (res) {
      const wait = pending.get(res.reqId);
      if (wait && wait.cmdId === res.cmdId) {
        clearTimeout(wait.timer);
        pending.delete(res.reqId);
        wait.resolve(res);
      }
      if (res.cmdId === BS_CMD_BLE_POLICY_SET && res.status === 0 && res.body.byteLength > 0) {
        policyFlags = res.body[0]! & 0x3f;
      }
      return;
    }
    const evt = tryParseEvtSensor(frame);
    if (!evt) return;
    evtRawCount += 1;
    const sid = evt.sensorId;
    const counter = evt.counter;
    let set = seen.get(sid);
    if (!set) {
      set = new Set();
      seen.set(sid, set);
    }
    if (set.has(counter)) return;
    set.add(counter);
    if (set.size > 256) {
      seen.set(sid, new Set([counter]));
    }
    const sample = mapSensorSample(evt);
    if (!sample) return;
    latest.set(sid, sample);
    counts.set(sid, (counts.get(sid) ?? 0) + 1);
    events.onSample?.(sample);
  };

  const onChunk = (chunk: Uint8Array) => {
    if (chunk.byteLength === 0) return;
    events.onRawNotify?.(chunk);
    let frame: Uint8Array | null = null;
    if (chunk[0] === BS2_BLE_CHUNK_VER) {
      frame = reassembler.feed(chunk);
    } else if (looksLikeBsPrefix(chunk)) {
      reassembler.reset();
      frame = chunk;
    }
    if (frame) handleFrame(frame);
  };

  const writeReqFire = async (cmdId: number, body: Uint8Array = new Uint8Array()) => {
    const reqId = nextReqId;
    nextReqId = (nextReqId + 1) & 0xffff || 1;
    const wire = encodeBsReq(reqId, cmdId, body);
    await transport.writeRx(wire, false);
  };

  const request = async (
    cmdId: number,
    body: Uint8Array = new Uint8Array(),
    opts: { timeoutMs?: number } = {},
  ): Promise<Bs2Res> => {
    if (!transport.isConnected()) {
      throw new Error("not connected");
    }
    if (!notifyOn) {
      throw new Error("start notify (goLive / enableStreaming) before waiting for RES");
    }
    const timeoutMs = opts.timeoutMs ?? 6000;
    const reqId = nextReqId;
    nextReqId = (nextReqId + 1) & 0xffff || 1;
    const wire = encodeBsReq(reqId, cmdId, body);

    return new Promise<Bs2Res>((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(reqId);
        reject(new Error(`REQ timeout cmd=0x${cmdId.toString(16)} reqId=${reqId}`));
      }, timeoutMs);
      pending.set(reqId, { cmdId, resolve, reject, timer });
      void transport.writeRx(wire, false).catch((e) => {
        clearTimeout(timer);
        pending.delete(reqId);
        reject(e instanceof Error ? e : new Error(String(e)));
      });
    });
  };

  const ensureNotify = async (settleMs: number) => {
    if (!transport.isConnected()) {
      throw new Error("not connected");
    }
    if (!notifyOn) {
      await transport.startNotify(onChunk);
      notifyOn = true;
      await sleep(settleMs);
    }
  };

  const setBlePolicy = async (
    flags: number,
    opts: { timeoutMs?: number; attempts?: number } = {},
  ): Promise<number> => {
    const want = flags & 0x3f;
    if (policyFlags === want && transport.isConnected()) {
      return want;
    }
    const attempts = Math.max(1, opts.attempts ?? 3);
    const timeoutMs = opts.timeoutMs ?? 8000;
    let lastErr: Error | null = null;
    for (let i = 0; i < attempts; i++) {
      try {
        const res = await request(BS_CMD_BLE_POLICY_SET, Uint8Array.of(want), { timeoutMs });
        if (res.status !== 0) {
          throw new Error(`BLE_POLICY_SET status=${res.status}`);
        }
        policyFlags = res.body.byteLength > 0 ? res.body[0]! & 0x3f : want;
        return policyFlags;
      } catch (e) {
        lastErr = e instanceof Error ? e : new Error(String(e));
        log("warn", `BLE_POLICY_SET attempt ${i + 1}/${attempts}: ${lastErr.message}`);
        await sleep(250 * (i + 1));
      }
    }
    throw lastErr ?? new Error("BLE_POLICY_SET failed");
  };

  const ping = async (opts: { timeoutMs?: number; attempts?: number } = {}): Promise<Bs2Res> => {
    const attempts = Math.max(1, opts.attempts ?? 3);
    const timeoutMs = opts.timeoutMs ?? 6000;
    let lastErr: Error | null = null;
    for (let i = 0; i < attempts; i++) {
      try {
        const res = await request(BS_CMD_PING, new Uint8Array(), { timeoutMs });
        if (res.status !== 0) {
          throw new Error(`PING status=${res.status}`);
        }
        log("info", `PING RES reqId=${res.reqId} status=0`);
        return res;
      } catch (e) {
        lastErr = e instanceof Error ? e : new Error(String(e));
        log("warn", `PING attempt ${i + 1}/${attempts}: ${lastErr.message}`);
        await sleep(250 * (i + 1));
      }
    }
    throw lastErr ?? new Error("PING failed");
  };

  return {
    async connect() {
      setPhase("connecting");
      try {
        device = await transport.connect();
        setPhase("linked");
        log("info", `Connected ${device.name} (${device.address})`);
        try {
          const raw = await transport.readLink();
          events.onLink?.(decodeLinkSnapshot(raw));
        } catch (e) {
          log("warn", `BS_LINK read skipped: ${e instanceof Error ? e.message : String(e)}`);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        const cancelled =
          /cancelled|canceled|chooser/i.test(msg) ||
          (e instanceof Error && e.name === "AbortError");
        try {
          await transport.disconnect();
        } catch {
          /* ignore */
        }
        device = null;
        if (cancelled) {
          setPhase("idle");
          log("info", "Connect cancelled");
        } else {
          setPhase("error");
          log("error", msg);
        }
        throw e;
      }
    },

    async disconnect() {
      rejectAllPending("disconnected");
      try {
        if (notifyOn) await transport.stopNotify();
      } catch {
        /* ignore */
      }
      notifyOn = false;
      reassembler.reset();
      seen.clear();
      evtRawCount = 0;
      policyFlags = 0;
      try {
        await transport.disconnect();
      } catch {
        /* ignore */
      }
      device = null;
      setPhase("idle");
      log("info", "Disconnected");
    },

    async goLive(settleMs = 800) {
      await ensureNotify(settleMs);
      setPhase("live");
      log("info", "Live: BS_TX notify on (TX_EVT via CCCD)");
    },

    async enableStreaming(opts = {}) {
      const settleMs = opts.settleMs ?? 400;
      const policyTimeoutMs = opts.policyTimeoutMs ?? 8000;
      const policyAttempts = opts.policyAttempts ?? 3;
      await ensureNotify(settleMs);
      setPhase("live");

      try {
        const flags = await setBlePolicy(BLE_POLICY_FACTORY_STREAMING, {
          timeoutMs: policyTimeoutMs,
          attempts: policyAttempts,
        });
        log("info", `Stream on — policy 0x${flags.toString(16)}`);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        const txEvt = (policyFlags & 0x02) !== 0;
        const evtFlowing = evtRawCount > 0;
        if (txEvt || evtFlowing) {
          log(
            "warn",
            `BLE_POLICY_SET incomplete; streaming anyway (policy=0x${policyFlags.toString(16)} evt_flowing=${evtFlowing}): ${msg}`,
          );
        } else {
          throw e instanceof Error ? e : new Error(msg);
        }
      }
    },

    ping,
    setBlePolicy,
    request,

    async applyCfgsFire(cfgs, gapMs = 50) {
      for (const cfg of cfgs) {
        await writeReqFire(BS_CMD_SENSOR_CFG_SET, encodeSensorCfgBody(cfg));
        await sleep(gapMs);
      }
    },

    writeReqFire,

    async readLink() {
      const raw = await transport.readLink();
      const snap = decodeLinkSnapshot(raw);
      events.onLink?.(snap);
      return snap;
    },

    getPhase: () => phase,
    getDevice: () => device,
    getLatest: () => latest,
    getCounts: () => counts,
    getPolicyFlags: () => policyFlags,
  };
}
