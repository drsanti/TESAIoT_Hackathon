/**
 * Fresh Chrome Web Bluetooth step diagnostic.
 * Does NOT use useBleSession / createWebBluetoothTransport / tbs-ble-session.
 *
 * Observed failure mode (Win Chrome): PASS connect, then link drops if we wait
 * before getPrimaryService - so discovery must start immediately after connect.
 */
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

const SERVICE = "6f6b7a80-0001-4000-8000-00805f9b34fb";
const BS_RX = "6f6b7a80-0001-4001-8000-00805f9b34fb";
const BS_TX = "6f6b7a80-0001-4002-8000-00805f9b34fb";
const BS_LINK = "6f6b7a80-0001-4003-8000-00805f9b34fb";
const NAME_PREFIX = "TESAIoT-";

type LogLevel = "info" | "ok" | "err";
type LogLine = { id: number; level: LogLevel; text: string };

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function BleStepDiagPage() {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [seq, setSeq] = useState(0);
  const [busy, setBusy] = useState(false);
  const [device, setDevice] = useState<BluetoothDevice | null>(null);
  const [server, setServer] = useState<BluetoothRemoteGATTServer | null>(null);
  const [service, setService] = useState<BluetoothRemoteGATTService | null>(null);
  const [chars, setChars] = useState<{
    rx: BluetoothRemoteGATTCharacteristic | null;
    tx: BluetoothRemoteGATTCharacteristic | null;
    link: BluetoothRemoteGATTCharacteristic | null;
  }>({ rx: null, tx: null, link: null });

  const connectAtMs = useRef(0);
  const disconnectHook = useRef<((ev: Event) => void) | null>(null);
  /** Sync guard - React state `busy` is too slow and allowed double Run-all (two connects). */
  const busyRef = useRef(false);
  /** Avoid nesting setLogs inside setSeq - Strict Mode double-invokes updaters and duplicated every line. */
  const logIdRef = useRef(0);

  const log = (level: LogLevel, text: string) => {
    logIdRef.current += 1;
    const id = logIdRef.current;
    setSeq(id);
    setLogs((prev) => [{ id, level, text }, ...prev].slice(0, 100));
  };

  const withBusy = async (label: string, fn: () => Promise<void>) => {
    if (busyRef.current) {
      log("info", `Skipped (already running): ${label}`);
      return;
    }
    busyRef.current = true;
    setBusy(true);
    log("info", `→ ${label}`);
    try {
      await fn();
    } catch (e) {
      const msg = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
      log("err", `FAIL ${label} - ${msg}`);
      if (
        /GATT Server is disconnected|stillConnected=false|gattserverdisconnected|GATT dropped before discover|GATT not connected/i.test(
          msg,
        )
      ) {
        log(
          "err",
          "Recovery: Task Manager End ALL chrome.exe until 0 → RESET soft-blue → remove any TESAIoT pair " +
            "(do NOT re-pair yet) → ONLY Edge → hard-reload → use Run all (acceptAll) ONCE.",
        );
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const armDisconnectWatch = (d: BluetoothDevice) => {
    if (disconnectHook.current) {
      d.removeEventListener("gattserverdisconnected", disconnectHook.current);
    }
    const handler = () => {
      const dt = connectAtMs.current ? Math.round(performance.now() - connectAtMs.current) : -1;
      setServer(null);
      setService(null);
      setChars({ rx: null, tx: null, link: null });
      log("err", `gattserverdisconnected after ${dt} ms since connect`);
    };
    disconnectHook.current = handler;
    d.addEventListener("gattserverdisconnected", handler);
  };

  const doSupport = async () => {
    if (!window.isSecureContext) throw new Error("not a secure context");
    if (!navigator.bluetooth?.requestDevice) throw new Error("navigator.bluetooth missing");
    log("ok", "PASS 1 - secure context + requestDevice");
  };

  const requestBoard = async (mode: "filtered" | "acceptAll") => {
    const d =
      mode === "acceptAll"
        ? await navigator.bluetooth.requestDevice({
            // WinRT: namePrefix+services in one filter can connect then abort (~10-100 ms).
            acceptAllDevices: true,
            optionalServices: [SERVICE],
          })
        : await navigator.bluetooth.requestDevice({
            filters: [{ namePrefix: NAME_PREFIX }, { services: [SERVICE] }],
            optionalServices: [SERVICE],
          });
    setDevice(d);
    setServer(null);
    setService(null);
    setChars({ rx: null, tx: null, link: null });
    armDisconnectWatch(d);
    log("ok", `PASS 2 - ${d.name ?? "(unnamed)"} id=${d.id} mode=${mode}`);
    return d;
  };

  const doRequest = async () => {
    await requestBoard("filtered");
  };

  const doConnect = async (d: BluetoothDevice) => {
    if (!d.gatt) throw new Error("device.gatt is null");
    armDisconnectWatch(d);
    if (d.gatt.connected) {
      d.gatt.disconnect();
      await sleep(300);
    }
    const s = await d.gatt.connect();
    connectAtMs.current = performance.now();
    setServer(s);
    setService(null);
    setChars({ rx: null, tx: null, link: null });
    // WinRT often flips connected=false within the same turn after connect resolves.
    const still = Boolean(d.gatt?.connected && s.connected);
    log(
      still ? "ok" : "err",
      `PASS 3 - connect resolved connected=${s.connected} live=${still}` +
        (still ? " (discover ASAP)" : " (link already dropped - will reconnect in step 4)"),
    );
    return s;
  };

  /**
   * Discover immediately. If WinRT already dropped the link after connect resolved,
   * reconnect once and discover in the same turn (no UI settle gap).
   */
  const doService = async (d: BluetoothDevice) => {
    const ensureUp = async () => {
      if (d.gatt?.connected) return d.gatt;
      log("info", "GATT down before discover - reconnect once");
      await doConnect(d);
      if (!d.gatt?.connected) {
        const dt = connectAtMs.current
          ? Math.round(performance.now() - connectAtMs.current)
          : -1;
        throw new Error(
          `GATT dropped before discover (${dt} ms since connect). ` +
            `Quit every chrome.exe, soft-blue ADV, Edge only, Run all (acceptAll).`,
        );
      }
      return d.gatt;
    };

    let gatt = await ensureUp();
    const t0 = performance.now();
    try {
      // Kick UUID lookup first (no await on enum) - race the WinRT drop window.
      const svcPromise = gatt.getPrimaryService(SERVICE);
      try {
        const all = await gatt.getPrimaryServices();
        log(
          "info",
          `services enum=${all.length} (${all.map((x) => x.uuid).join(", ") || "none"})`,
        );
      } catch {
        /* optional */
      }
      const svc = await svcPromise;
      setService(svc);
      setChars({ rx: null, tx: null, link: null });
      log("ok", `PASS 4 - service ${svc.uuid} (${Math.round(performance.now() - t0)} ms)`);
      return svc;
    } catch (e) {
      if (!d.gatt?.connected) {
        log("info", "discover failed with link down - one reconnect+retry");
        gatt = await ensureUp();
        const svc = await gatt.getPrimaryService(SERVICE);
        setService(svc);
        setChars({ rx: null, tx: null, link: null });
        log("ok", `PASS 4 - service ${svc.uuid} after reconnect (${Math.round(performance.now() - t0)} ms)`);
        return svc;
      }
      const still = gatt.connected;
      const dt = Math.round(performance.now() - connectAtMs.current);
      throw new Error(
        `${e instanceof Error ? e.message : String(e)} | stillConnected=${still} | ${dt} ms since connect`,
      );
    }
  };

  const doChars = async (svc: BluetoothRemoteGATTService) => {
    const rx = await svc.getCharacteristic(BS_RX);
    const tx = await svc.getCharacteristic(BS_TX);
    const link = await svc.getCharacteristic(BS_LINK);
    setChars({ rx, tx, link });
    log(
      "ok",
      `PASS 5 - RX/TX/LINK ok (TX.notify=${String(tx.properties.notify)})`,
    );
    return { rx, tx, link };
  };

  const doReadLink = async (link: BluetoothRemoteGATTCharacteristic) => {
    const value = await link.readValue();
    const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
    log("ok", `PASS 6 - BS_LINK len=${bytes.length} hex=${hex} state=${bytes[0] ?? "?"}`);
  };

  const doNotify = async (tx: BluetoothRemoteGATTCharacteristic) => {
    let n = 0;
    const handler = () => {
      n += 1;
    };
    tx.addEventListener("characteristicvaluechanged", handler);
    await tx.startNotifications();
    await sleep(2500);
    await tx.stopNotifications();
    tx.removeEventListener("characteristicvaluechanged", handler);
    log("ok", `PASS 7 - notify on; ${n} chunk(s) in 2.5s (0 OK without stream CFG)`);
  };

  const runAllFresh = (mode: "filtered" | "acceptAll") =>
    withBusy(`ALL 1→6 (${mode})`, async () => {
      await doSupport();
      const d = await requestBoard(mode);
      // Connect + discover back-to-back; doService reconnects if WinRT drops mid-turn.
      await doConnect(d);
      const svc = await doService(d);
      const c = await doChars(svc);
      await doReadLink(c.link!);
      log("info", "ALL 1→6 complete - optional: step 7 Notify");
    });

  const onRunAll = () => {
    if (busy) return;
    void runAllFresh("filtered");
  };

  const onRunAllAcceptAll = () => {
    if (busy) return;
    void runAllFresh("acceptAll");
  };

  return (
    <div>
      <p className="muted">
        <Link to="/">← Labs catalog</Link>
      </p>
      <h1 style={{ margin: "0.35rem 0 0.5rem", fontSize: "1.35rem" }}>BLE step diagnostic (fresh)</h1>
      <p className="muted">
        Win Chrome often drops GATT if we wait after connect. This page discovers{" "}
        <strong>immediately</strong> after step 3. Soft-blue ADV before step 2.
      </p>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h2>Chrome / Edge</h2>
        <div className="btn-row" style={{ flexWrap: "wrap" }}>
          <button className="primary" type="button" disabled={busy} onClick={onRunAllAcceptAll}>
            Run all (acceptAll)
          </button>
          <button type="button" disabled={busy} onClick={onRunAll}>
            Run all (filtered)
          </button>
          <button type="button" disabled={busy} onClick={() => void withBusy("1 Support", doSupport)}>
            1 Support
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void withBusy("2 Request device", doRequest)}
          >
            2 Request device
          </button>
          <button
            type="button"
            disabled={busy || !device}
            onClick={() =>
              void withBusy("3 GATT connect", async () => {
                if (!device) throw new Error("run step 2 first");
                await doConnect(device);
              })
            }
          >
            3 GATT connect
          </button>
          <button
            type="button"
            disabled={busy || !device}
            onClick={() =>
              void withBusy("4 Service (immediate)", async () => {
                if (!device) throw new Error("run step 2–3 first");
                await doService(device);
              })
            }
          >
            4 Service
          </button>
          <button
            type="button"
            disabled={busy || !service}
            onClick={() =>
              void withBusy("5 Chars", async () => {
                if (!service) throw new Error("run step 4 first");
                await doChars(service);
              })
            }
          >
            5 Chars
          </button>
          <button
            type="button"
            disabled={busy || !chars.link}
            onClick={() =>
              void withBusy("6 Read LINK", async () => {
                if (!chars.link) throw new Error("run step 5 first");
                await doReadLink(chars.link);
              })
            }
          >
            6 Read LINK
          </button>
          <button
            type="button"
            disabled={busy || !chars.tx}
            onClick={() =>
              void withBusy("7 Notify", async () => {
                if (!chars.tx) throw new Error("run step 5 first");
                await doNotify(chars.tx);
              })
            }
          >
            7 Notify
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void withBusy("Disconnect", async () => {
                try {
                  if (chars.tx) {
                    try {
                      await chars.tx.stopNotifications();
                    } catch {
                      /* ignore */
                    }
                  }
                  if (device?.gatt?.connected) device.gatt.disconnect();
                  else if (server?.connected) server.disconnect();
                } finally {
                  setServer(null);
                  setService(null);
                  setChars({ rx: null, tx: null, link: null });
                  log("ok", "Disconnected. Run step 2 again before reconnect (RPA may rotate).");
                }
              })
            }
          >
            Disconnect
          </button>
        </div>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          State: device={device?.name ?? "-"} · gatt=
          {server?.connected || device?.gatt?.connected ? "up" : "down"} · service=
          {service ? "yes" : "no"} · chars={chars.link ? "yes" : "no"} · seq={seq}
        </p>
      <p className="err" style={{ marginTop: "0.75rem" }}>
        <strong>If drop at ~10-100 ms:</strong> WinRT aborted GATT. On this PC we keep finding live{" "}
        <code>chrome.exe</code> while you try Edge - that alone causes this. Host bleak still PASS.
      </p>
      <ol className="muted" style={{ marginTop: "0.35rem", paddingLeft: "1.25rem" }}>
        <li>
          Task Manager → End <strong>every</strong> <code>chrome.exe</code> until <strong>0</strong>.
          Leave Chrome closed for the whole session.
        </li>
        <li>
          Soft-blue ADV (RESET / TFT Reset BLE). In Bluetooth settings,{" "}
          <strong>remove</strong> any <code>TESAIoT-*</code> - do <em>not</em> re-pair yet (bond
          mismatch with firmware NO_BOND can abort ~80 ms after connect).
        </li>
        <li>
          <strong>Edge only</strong> → hard-reload → primary button{" "}
          <strong>Run all (acceptAll)</strong> → pick <code>TESAIoT-*</code> in the chooser.
        </li>
      </ol>
      <p className="warn" style={{ marginTop: "0.5rem" }}>
        Recommended on this PC: skip Web Bluetooth — start{" "}
        <code>tools/ble-bridge</code> (<code>npm start</code>) and open{" "}
        <Link to="/?ble=bridge">labs with Host bridge</Link>.
      </p>
      </div>

      <div className="panel">
        <h2>Log</h2>
        {logs.length === 0 ? (
          <p className="muted">No steps yet.</p>
        ) : (
          <ul className="checklist">
            {logs.map((line) => (
              <li key={line.id}>
                <span className={line.level === "ok" ? "ok" : line.level === "err" ? "err" : "muted"}>
                  {line.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h2>Host checks (separate process)</h2>
        <pre className="muted" style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>
          {`# Node BLE bridge (recommended for labs UI)
cd TESAIoT_Hackathon/ble-react/tools/ble-bridge
npm install && npm start
# then http://localhost:5174/?ble=bridge

# Python / bleak (reference GATT proof)
cd TESAIoT_Hackathon/python-app
./.venv/Scripts/python.exe tools/ble_step_diag.py`}
        </pre>
        <p className="muted">
          Disconnect this page first. Host PASS + Chrome drop-after-connect = Windows browser BLE stack.
        </p>
      </div>
    </div>
  );
}
