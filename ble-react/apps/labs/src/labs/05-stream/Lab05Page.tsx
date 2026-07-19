import { useEffect, useState } from "react";
import { ALL_SENSOR_IDS, SENSOR_NAMES } from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";
import { goLiveAllSensorsHybrid } from "../goLiveAllHybrid";

export function Lab05Page() {
  const { phase, connect, goLive, enableStreaming, applyCfgsFire, writeReqFire, counts, clearCounts } =
    useBleSession();
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("05");

  useEffect(() => {
    if (!running) return;
    const t0 = Date.now();
    const id = window.setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 250);
    return () => window.clearInterval(id);
  }, [running]);

  const start = async () => {
    clearCounts();
    setElapsed(0);
    setRunning(false);
    setStatus("Applying hybrid CFG for all six sensors…");
    try {
      if (phase === "idle" || phase === "error") {
        await connect();
      }
      await goLiveAllSensorsHybrid(
        { goLive, enableStreaming, writeReqFire, applyCfgsFire },
        { alreadyLive: phase === "live" },
      );
      setStatus("Hybrid stream on — counters should climb.");
      setRunning(true);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  };

  const total = ALL_SENSOR_IDS.reduce((sum: number, id) => sum + (counts.get(id) ?? 0), 0);
  const zeros = ALL_SENSOR_IDS.filter((id) => (counts.get(id) ?? 0) === 0);
  const allLive = zeros.length === 0 && total > 0;

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Continuous streaming needs a stable GATT session. Connect (or reuse the shared session
          from earlier chapters).
        </p>
      ),
      do: <ConnectBar />,
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "stream",
      title: "Hybrid soak (≥15s)",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          <strong>Reset &amp; stream</strong> enables notifications and applies hybrid publish for
          all six sensors (including pots/buttons on a periodic cadence). Watch every counter climb
          for at least 15 seconds.
        </p>
      ),
      do: (
        <div>
          <div className="btn-row">
            <button
              className="primary"
              type="button"
              disabled={phase === "connecting" || phase === "error"}
              onClick={() => void start()}
            >
              Reset &amp; stream
            </button>
            <button type="button" disabled={!running} onClick={() => setRunning(false)}>
              Stop timer
            </button>
          </div>
          <p className="muted" style={{ marginTop: "0.65rem" }}>
            Timer: <strong className={running ? "ok" : undefined}>{running ? "running" : "stopped"}</strong>
            {" · "}
            Elapsed: {elapsed}s · total samples: {total}
          </p>
          {status ? <p className="muted">{status}</p> : null}
          <ul className="checklist">
            {ALL_SENSOR_IDS.map((id) => (
              <li key={id}>
                {SENSOR_NAMES[id]}:{" "}
                <strong className={(counts.get(id) ?? 0) > 0 ? "ok" : undefined}>
                  {counts.get(id) ?? 0}
                </strong>
              </li>
            ))}
          </ul>
        </div>
      ),
      callout: (
        <Callout variant="info" title="Timer vs BLE">
          <strong>Stop timer</strong> only freezes the elapsed clock. Use <strong>Disconnect</strong>{" "}
          to stop notifications.
        </Callout>
      ),
      checks: [
        {
          id: "time",
          label: "Acceptance window ≥ 15 seconds",
          pass: elapsed >= 15,
        },
        {
          id: "all",
          label: "All six sensors published at least once",
          pass: allLive,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="05"
      title="Prove the stream"
      subtitle="Show that hybrid publish keeps all sensors ticking over a short soak."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    />
  );
}
