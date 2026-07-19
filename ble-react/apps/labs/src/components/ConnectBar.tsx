import { Link } from "react-router-dom";
import { useBleSession } from "../hooks/useBleSession";
import { Callout } from "../tutorial";

export function ConnectBar({ hint }: { hint?: string }) {
  const {
    phase,
    device,
    connect,
    disconnect,
    lastError,
    logs,
    transportMode,
    setTransportMode,
  } = useBleSession();
  const busy = phase === "connecting";
  const linked = phase === "linked" || phase === "live";
  const needsPairHelp =
    transportMode === "web" &&
    (phase === "error" ||
      (lastError != null &&
        /RESET|Connection failed|GATT dropped|GATT disconnected|no longer in range/i.test(
          lastError,
        )));

  return (
    <div className="panel connect-panel">
      <h2>Connection</h2>
      {hint ? (
        <p className="muted" style={{ marginTop: 0 }}>
          {hint}
        </p>
      ) : null}

      <div className="btn-row" style={{ marginTop: "0.55rem", flexWrap: "wrap" }}>
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
      <p className="muted" style={{ marginTop: "0.4rem", marginBottom: 0, fontSize: "0.85rem" }}>
        {transportMode === "bridge" ? (
          <>
            Mode: <strong>host Node bridge</strong> at <code>ws://127.0.0.1:9788</code> (Node WS +
            bleak radio). Run <code>pnpm bridge</code> from <code>ble-react</code>.
          </>
        ) : (
          <>
            Mode: <strong>browser Web Bluetooth</strong> (often drops on Windows WinRT).
          </>
        )}
      </p>

      <div className="btn-row" style={{ marginTop: "0.55rem" }}>
        <button
          className="primary"
          type="button"
          disabled={busy || linked}
          onClick={() => void connect()}
        >
          {busy ? "Connecting…" : phase === "error" ? "Retry connect" : "Connect"}
        </button>
        <button type="button" disabled={!linked && phase !== "error"} onClick={() => void disconnect()}>
          Disconnect
        </button>
      </div>
      <p className="muted" style={{ marginTop: "0.65rem", marginBottom: 0 }}>
        Phase: <strong>{phase}</strong>
        {device ? (
          <>
            {" "}
            · {device.name} <span className="mono">({device.address})</span>
          </>
        ) : null}
      </p>
      {lastError ? (
        <p className="err" style={{ marginTop: "0.5rem", marginBottom: 0 }}>
          {lastError}
        </p>
      ) : null}
      {logs.length > 0 ? (
        <details style={{ marginTop: "0.55rem" }}>
          <summary>Connection log</summary>
          <pre className="log-pre">{logs.join("\n")}</pre>
        </details>
      ) : null}
      {transportMode === "bridge" ? (
        <Callout variant="info" title="Host bridge">
          Run <code>pnpm bridge</code> (Node WebSocket + python-app bleak). Soft-blue ADV, no competing
          Chrome GATT, then Connect. Bypasses Windows browser Web Bluetooth.
        </Callout>
      ) : needsPairHelp ? (
        <Callout variant="warn" title="Windows Web Bluetooth tip">
          Prefer <strong>Host bridge (Node)</strong> on this PC. Or pair <code>TESAIoT-*</code> in
          Settings, RESET soft-blue, retry — see <Link to="/diag">/diag</Link>.
        </Callout>
      ) : (
        <p className="muted" style={{ marginTop: "0.55rem", marginBottom: 0, fontSize: "0.85rem" }}>
          On Windows, use <strong>Host bridge</strong> if Web Bluetooth drops after connect.
        </p>
      )}
    </div>
  );
}
