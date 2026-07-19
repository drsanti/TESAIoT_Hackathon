/**
 * Spawn python-app bleak worker (JSON lines) — proven WinRT GATT on this PC.
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function resolvePython() {
  if (process.env.TBS_BLE_PYTHON) return process.env.TBS_BLE_PYTHON;
  const hackathon = path.resolve(__dirname, "../../../../python-app");
  const win = path.join(hackathon, ".venv", "Scripts", "python.exe");
  const nix = path.join(hackathon, ".venv", "bin", "python");
  return process.platform === "win32" ? win : nix;
}

export function createBleakBackend({ onLog, onDisconnected, onNotify }) {
  let child = null;
  let connected = false;
  let pending = null;

  const sendCmd = (obj) => {
    if (!child?.stdin?.writable) throw new Error("bleak worker not running");
    child.stdin.write(JSON.stringify(obj) + "\n");
  };

  const ensureWorker = () => {
    if (child) return;
    const py = resolvePython();
    const script = path.join(__dirname, "ble_worker.py");
    onLog?.("info", `starting bleak worker: ${py}`);
    child = spawn(py, [script], {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    const rl = createInterface({ input: child.stdout });
    rl.on("line", (line) => {
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        onLog?.("warn", `worker bad line: ${line.slice(0, 120)}`);
        return;
      }
      const ev = msg.event;
      if (ev === "log") {
        onLog?.(msg.level === "error" || msg.level === "warn" ? msg.level : "info", msg.message);
        return;
      }
      if (ev === "notify") {
        onNotify?.(Buffer.from(String(msg.data || ""), "base64"));
        return;
      }
      if (ev === "disconnected") {
        connected = false;
        onDisconnected?.(msg.reason ?? "link-down");
      }
      if (pending && pending.match(msg)) {
        const p = pending;
        pending = null;
        if (ev === "error") p.reject(new Error(msg.message || "worker error"));
        else p.resolve(msg);
      } else if (ev === "error") {
        onLog?.("error", msg.message || "worker error");
      }
    });
    child.stderr.on("data", (buf) => {
      const t = String(buf).trim();
      if (t) onLog?.("warn", `worker stderr: ${t.slice(0, 200)}`);
    });
    child.on("exit", (code) => {
      onLog?.("warn", `bleak worker exited code=${code}`);
      child = null;
      connected = false;
      if (pending) {
        pending.reject(new Error("bleak worker exited"));
        pending = null;
      }
      onDisconnected?.("worker-exit");
    });
  };

  const request = (cmdObj, matchEvent, timeoutMs = 60_000) => {
    ensureWorker();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (pending) {
          pending = null;
          reject(new Error(`timeout waiting for ${matchEvent}`));
        }
      }, timeoutMs);
      pending = {
        match: (m) => m.event === matchEvent || m.event === "error",
        resolve: (m) => {
          clearTimeout(timer);
          resolve(m);
        },
        reject: (e) => {
          clearTimeout(timer);
          reject(e);
        },
      };
      sendCmd(cmdObj);
    });
  };

  return {
    async connect() {
      const msg = await request({ cmd: "connect" }, "connected", 90_000);
      connected = true;
      return {
        name: msg.name || "TESAIoT",
        address: msg.address || "",
        chars: msg.chars || [],
      };
    },

    async disconnect() {
      try {
        if (child) await request({ cmd: "disconnect" }, "disconnected", 10_000);
      } catch {
        /* ignore */
      }
      connected = false;
      try {
        child?.kill();
      } catch {
        /* ignore */
      }
      child = null;
    },

    isConnected() {
      return connected;
    },

    async startNotify() {
      await request({ cmd: "start_notify" }, "notify_started", 15_000);
    },

    async stopNotify() {
      try {
        await request({ cmd: "stop_notify" }, "notify_stopped", 8_000);
      } catch {
        /* ignore */
      }
    },

    async writeRx(dataB64, withResponse = false) {
      await request(
        { cmd: "write_rx", data: dataB64, withResponse: Boolean(withResponse) },
        "write_ok",
        15_000,
      );
    },

    async readLink() {
      const msg = await request({ cmd: "read_link" }, "link", 15_000);
      return String(msg.data || "");
    },
  };
}
