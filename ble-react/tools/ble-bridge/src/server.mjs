/**
 * Node BLE → WebSocket bridge for ble-react labs.
 *
 *   cd tools/ble-bridge && npm install && npm start
 *   Labs: ?ble=bridge  or ConnectBar → Host bridge
 *
 * Default: ws://127.0.0.1:9788
 */
import { WebSocketServer } from "ws";
import { createBleakBackend } from "./ble-backend-bleak.mjs";

const PORT = Number(process.env.TBS_BLE_BRIDGE_PORT || 9788);
const HOST = process.env.TBS_BLE_BRIDGE_HOST || "127.0.0.1";

function send(ws, msg) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

function broadcast(wss, msg, except = null) {
  const raw = JSON.stringify(msg);
  for (const client of wss.clients) {
    if (client !== except && client.readyState === client.OPEN) {
      client.send(raw);
    }
  }
}

async function main() {
  /** @type {import("ws").WebSocket | null} */
  let owner = null;

  // Bleak worker: proven full GATT on Windows. (webbluetooth SimpleBLE often sees 0 chars.)
  const backend = createBleakBackend({
    onLog: (level, message) => {
      console.log(`[${level}] ${message}`);
      if (owner) send(owner, { type: "log", level, message });
    },
    onDisconnected: (reason) => {
      console.warn(`[warn] BLE disconnected: ${reason ?? ""}`);
      if (owner) send(owner, { type: "disconnected", reason: reason ?? "link-down" });
    },
    onNotify: (chunk) => {
      const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      if (owner) send(owner, { type: "notify", data: buf.toString("base64") });
    },
  });

  const wss = new WebSocketServer({ host: HOST, port: PORT });
  console.log(`TESAIoT BLE bridge listening on ws://${HOST}:${PORT}`);
  console.log("Backend: Node control plane + Python bleak worker (python-app .venv)");
  console.log("Close Chrome/Edge GATT tabs first (one central). Soft-blue ADV on board.");

  wss.on("connection", (ws) => {
    console.log("[info] client connected");
    send(ws, {
      type: "hello",
      version: 1,
      port: PORT,
      backend: "bleak-worker",
      hint: "Send {type:\"connect\"} when TFT is soft-blue.",
    });

    ws.on("message", async (raw) => {
      let msg;
      try {
        msg = JSON.parse(String(raw));
      } catch {
        send(ws, { type: "error", message: "invalid JSON" });
        return;
      }

      const type = msg?.type;
      try {
        switch (type) {
          case "ping":
            send(ws, { type: "pong", t: Date.now() });
            break;

          case "connect": {
            if (owner && owner !== ws && owner.readyState === owner.OPEN) {
              console.warn("[warn] stealing bridge from previous owner tab");
              try {
                send(owner, {
                  type: "disconnected",
                  reason: "bridge-stolen",
                });
                owner.close();
              } catch {
                /* ignore */
              }
              owner = null;
              try {
                await backend.disconnect();
              } catch {
                /* ignore */
              }
              // Let WinRT / bleak worker fully release before re-scan.
              await new Promise((r) => setTimeout(r, 800));
            }
            owner = ws;
            send(ws, { type: "status", phase: "connecting" });
            const info = await backend.connect();
            send(ws, {
              type: "connected",
              name: info.name,
              address: info.address,
              chars: info.chars,
            });
            break;
          }

          case "disconnect": {
            await backend.disconnect();
            if (owner === ws) owner = null;
            send(ws, { type: "disconnected", reason: "client-disconnect" });
            break;
          }

          case "start_notify":
            await backend.startNotify();
            send(ws, { type: "notify_started" });
            break;

          case "stop_notify":
            await backend.stopNotify();
            send(ws, { type: "notify_stopped" });
            break;

          case "write_rx":
            await backend.writeRx(msg.data, Boolean(msg.withResponse));
            send(ws, { type: "write_ok" });
            break;

          case "read_link": {
            const data = await backend.readLink();
            send(ws, { type: "link", data });
            break;
          }

          default:
            send(ws, { type: "error", message: `unknown type: ${type}` });
        }
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        console.error(`[error] ${type}: ${message}`);
        send(ws, { type: "error", message, op: type });
      }
    });

    ws.on("close", async () => {
      console.log("[info] client disconnected");
      if (owner === ws) {
        owner = null;
        try {
          await backend.disconnect();
        } catch {
          /* ignore */
        }
        broadcast(wss, { type: "log", level: "info", message: "bridge owner released" });
      }
    });
  });
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
