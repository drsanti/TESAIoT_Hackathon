import type { ReactNode } from "react";
import { useBleSession } from "../hooks/useBleSession";

export function ConnectBar({ hint }: { hint?: string }) {
  const { phase, device, connect, disconnect, lastError, logs } = useBleSession();
  const busy = phase === "connecting";
  const linked = phase === "linked" || phase === "live";
  const needsReset =
    phase === "error" ||
    (lastError != null && /RESET|Connection failed|GATT dropped/i.test(lastError));

  return (
    <div className="panel">
      <h2>Connection</h2>
      {hint ? <p className="muted">{hint}</p> : null}
      <div className="btn-row" style={{ marginTop: "0.5rem" }}>
        <button
          className="primary"
          type="button"
          disabled={busy || linked}
          onClick={() => void connect()}
        >
          {busy ? "Connecting… (may take ~5s)" : phase === "error" ? "Retry connect" : "Connect"}
        </button>
        <button
          type="button"
          disabled={!linked && phase !== "error"}
          onClick={() => void disconnect()}
        >
          Disconnect
        </button>
      </div>
      <p className="muted" style={{ marginTop: "0.65rem" }}>
        Phase: <strong>{phase}</strong>
        {device ? (
          <>
            {" "}
            · {device.name} <span>({device.address})</span>
          </>
        ) : null}
      </p>
      {lastError ? (
        <p className="err" style={{ marginTop: "0.5rem" }}>
          {lastError}
        </p>
      ) : null}
      {phase === "error" && !lastError && logs[0] ? (
        <p className="err" style={{ marginTop: "0.5rem" }}>
          {logs[0]}
        </p>
      ) : null}
      {logs.length > 0 ? (
        <details style={{ marginTop: "0.5rem" }}>
          <summary className="muted" style={{ fontSize: "0.85rem", cursor: "pointer", userSelect: "none" }}>
            Connection Logs
          </summary>
          <pre style={{
            background: "#111b27",
            color: "#a9b7c6",
            padding: "0.5rem",
            borderRadius: "4px",
            fontSize: "0.75rem",
            maxHeight: "150px",
            overflowY: "auto",
            marginTop: "0.25rem",
            whiteSpace: "pre-wrap",
            textAlign: "left",
            fontFamily: "monospace"
          }}>
            {logs.join("\n")}
          </pre>
        </details>
      ) : null}
      {needsReset ? (
        <ol className="muted" style={{ margin: "0.75rem 0 0", paddingLeft: "1.25rem" }}>
          <li>
            Press board <strong>RESET</strong> once.
          </li>
          <li>Wait until TFT is <strong>soft-blue</strong> (advertising again).</li>
          <li>Close nRF Connect / python-app / other Chrome tabs using this board.</li>
          <li>
            Click <strong>Retry connect</strong> and pick <code>TESAIoT-*</code>.
          </li>
        </ol>
      ) : (
        <p className="muted">
          After a failed connect, press board <strong>RESET</strong> until TFT soft-blue, then retry.
        </p>
      )}
    </div>
  );
}

export function LabLayout({
  labId,
  title,
  children,
}: {
  labId: string;
  title: string;
  children: ReactNode;
}) {
  const { phase } = useBleSession();
  return (
    <div>
      <p className="muted">
        <a href="/">← Labs catalog</a>
      </p>
      <h1 style={{ margin: "0.35rem 0 1rem", fontSize: "1.35rem" }}>
        Lab {labId}: {title}
      </h1>
      <div className={`status-pill ${phase === "live" ? "live" : phase === "error" ? "error" : ""}`}>
        Session: {phase}
      </div>
      <div style={{ marginTop: "1rem" }}>{children}</div>
    </div>
  );
}
