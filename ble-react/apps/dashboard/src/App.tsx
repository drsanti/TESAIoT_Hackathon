import { useState } from "react";
import {
  ALL_SENSOR_IDS,
  BLE_POLICY_FACTORY_STREAMING,
  formatLinkSnapshot,
} from "@ternion/tbs-core";
import { SensorCard } from "./components/SensorCard";
import { BleSessionProvider, useBleSession } from "./hooks/useBleSession";
import { goLiveAllSensorsHybrid } from "./goLiveAllHybrid";
import { detectWebBluetoothSupport } from "./transport/web-bluetooth";

type Tab = "connect" | "live" | "link" | "log";

function DashboardInner() {
  const support = detectWebBluetoothSupport();
  const {
    phase,
    device,
    link,
    latest,
    counts,
    logs,
    policyFlags,
    lastError,
    transportMode,
    setTransportMode,
    connect,
    disconnect,
    goLive,
    enableStreaming,
    ping,
    setBlePolicy,
    applyCfgsFire,
    writeReqFire,
    readLink,
  } = useBleSession();
  const [tab, setTab] = useState<Tab>("connect");
  const [linkBusy, setLinkBusy] = useState(false);
  const [linkMsg, setLinkMsg] = useState<string | null>(null);
  const linked = phase === "linked" || phase === "live";
  const busy = phase === "connecting";

  const streamOn = async () => {
    await goLiveAllSensorsHybrid(
      { goLive, enableStreaming, writeReqFire, applyCfgsFire },
      { alreadyLive: phase === "live" },
    );
    try {
      await readLink();
    } catch {
      /* optional */
    }
    setTab("live");
  };

  const runPing = async () => {
    setLinkBusy(true);
    setLinkMsg(null);
    try {
      if (phase !== "live") {
        await enableStreaming({ settleMs: 400 });
      }
      const res = await ping({ timeoutMs: 6000, attempts: 3 });
      setLinkMsg(`PING OK · reqId=${res.reqId} status=${res.status}`);
    } catch (e) {
      setLinkMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setLinkBusy(false);
    }
  };

  const runPolicyHeal = async () => {
    setLinkBusy(true);
    setLinkMsg(null);
    try {
      if (phase !== "live") {
        await enableStreaming({ settleMs: 400 });
      } else {
        await setBlePolicy(BLE_POLICY_FACTORY_STREAMING);
      }
      setLinkMsg(`POLICY 0x${BLE_POLICY_FACTORY_STREAMING.toString(16)} applied`);
    } catch (e) {
      setLinkMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setLinkBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">TESAIoT · BLE Dashboard</div>
        <div className={`status-pill ${phase === "live" ? "live" : phase === "error" ? "error" : ""}`}>
          {phase}
          {device ? ` · ${device.name}` : ""}
        </div>
      </header>

      <div className="btn-row" style={{ marginBottom: "1rem" }}>
        {(["connect", "live", "link", "log"] as Tab[]).map((t) => (
          <button key={t} type="button" className={tab === t ? "primary" : undefined} onClick={() => setTab(t)}>
            {t[0]!.toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "connect" ? (
        <div className="panel">
          <h2>Connect</h2>
          <div className="btn-row" style={{ marginBottom: "0.65rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className={transportMode === "bridge" ? "primary" : undefined}
              disabled={busy || linked}
              onClick={() => setTransportMode("bridge")}
            >
              Host bridge (Node)
            </button>
            <button
              type="button"
              className={transportMode === "web" ? "primary" : undefined}
              disabled={busy || linked}
              onClick={() => setTransportMode("web")}
            >
              Web Bluetooth
            </button>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {transportMode === "bridge" ? (
              <>
                Mode: <strong>host Node bridge</strong> at <code>ws://127.0.0.1:9788</code>. Run{" "}
                <code>pnpm bridge</code> from <code>ble-react</code>, then Connect (no Chrome GATT).
              </>
            ) : (
              <>
                Mode: <strong>browser Web Bluetooth</strong> — often drops on Windows WinRT. Prefer Host
                bridge on this PC.
              </>
            )}
          </p>
          <ul className="checklist">
            <li>
              Secure context:{" "}
              <strong className={support.secureContext ? "ok" : "err"}>
                {support.secureContext ? "yes" : "no"}
              </strong>
            </li>
            <li>
              Web Bluetooth:{" "}
              <strong className={support.supported ? "ok" : "err"}>
                {support.supported ? "available" : "unavailable"}
              </strong>
            </li>
            <li>Firmware advertising <code>TESAIoT-*</code> (TFT soft-blue)</li>
            <li>Only one BLE central connected</li>
          </ul>
          {!support.supported && transportMode === "web" ? (
            <p className="err">{support.reason}</p>
          ) : null}
          {lastError ? <p className="err">{lastError}</p> : null}
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button
              className="primary"
              type="button"
              disabled={busy || linked || (transportMode === "web" && !support.supported)}
              onClick={() => void connect()}
            >
              {busy ? "Connecting…" : phase === "error" ? "Retry connect" : "Connect"}
            </button>
            <button type="button" disabled={!linked && phase !== "error"} onClick={() => void disconnect()}>
              Disconnect
            </button>
            <button type="button" disabled={!linked} onClick={() => void streamOn()}>
              Stream on
            </button>
          </div>
          <p className="muted">
            Stream on: BS_TX notify + POLICY heal <code>0x07</code> + hybrid SENSOR_CFG for all six
            sensors. After a failed connect, press board RESET (or TFT Reset BLE).
          </p>
        </div>
      ) : null}

      {tab === "live" ? (
        <div>
          <div className="panel">
            <h2>Live sensors</h2>
            <p className="muted">Lab 10 graduation view — six teaching sensors.</p>
          </div>
          <div className="sensor-grid">
            {ALL_SENSOR_IDS.map((id) => (
              <SensorCard key={id} sensorId={id} sample={latest.get(id)} count={counts.get(id) ?? 0} />
            ))}
          </div>
        </div>
      ) : null}

      {tab === "link" ? (
        <div className="panel">
          <h2>Link</h2>
          <div className="btn-row">
            <button type="button" disabled={!linked || linkBusy} onClick={() => void readLink()}>
              Refresh BS_LINK
            </button>
            <button type="button" disabled={!linked || linkBusy} onClick={() => void runPing()}>
              PING
            </button>
            <button type="button" disabled={!linked || linkBusy} onClick={() => void runPolicyHeal()}>
              POLICY 0x07
            </button>
            <button type="button" disabled={!linked || linkBusy} onClick={() => void streamOn()}>
              Re-apply stream
            </button>
          </div>
          <p className="muted" style={{ marginTop: "0.5rem" }}>
            Session policy: <code>0x{policyFlags.toString(16)}</code>
            {policyFlags === BLE_POLICY_FACTORY_STREAMING ? " (ADV+TX_EVT+RX_REQ)" : ""}
          </p>
          {linkMsg ? (
            <p className={linkMsg.startsWith("PING OK") || linkMsg.startsWith("POLICY") ? "ok" : "err"}>
              {linkMsg}
            </p>
          ) : null}
          {link ? (
            <p className="ok" style={{ marginTop: "0.75rem" }}>
              {formatLinkSnapshot(link)}
            </p>
          ) : (
            <p className="muted">No link snapshot yet.</p>
          )}
        </div>
      ) : null}

      {tab === "log" ? (
        <div className="panel">
          <h2>Log</h2>
          <div className="log-box">{logs.join("\n") || "(empty)"}</div>
        </div>
      ) : null}
    </div>
  );
}

export function App() {
  return (
    <BleSessionProvider>
      <DashboardInner />
    </BleSessionProvider>
  );
}
