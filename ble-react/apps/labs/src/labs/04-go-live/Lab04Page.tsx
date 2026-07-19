import { useMemo, useState } from "react";
import { ALL_SENSOR_IDS, teachingHybridSensorCfgs } from "@ternion/tbs-core";
import { Link } from "react-router-dom";
import { ConnectBar } from "../../components/ConnectBar";
import { SensorCard } from "../../components/SensorCard";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

export function Lab04Page() {
  const {
    phase,
    connect,
    goLive,
    applyCfgsFire,
    latest,
    counts,
    sampleTick,
    clearCounts,
    lastError,
  } = useBleSession();
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("04");
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const hasAny = useMemo(
    () => ALL_SENSOR_IDS.some((id) => (counts.get(id) ?? 0) > 0 || latest.has(id)),
    [counts, latest, sampleTick],
  );

  const startNotifications = async () => {
    setActionError(null);
    setBusy(true);
    clearCounts();
    try {
      // Prefer the shared session from Chapter 03. Only connect when idle/error.
      if (phase === "idle" || phase === "error") {
        await connect();
      }
      // Short settle - long post-CCCD sleeps are a Windows drop risk.
      await goLive(100);
      // CCCD arms TX_EVT, but sensors still need hybrid CFG to publish EVTs.
      await applyCfgsFire(teachingHybridSensorCfgs(), 40);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const steps: TutorialStepDef[] = [
    {
      id: "link",
      title: "Stay connected",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Notifications need an open GATT session. If you finished Chapter 03 in this tab, you should
          already be <strong>linked</strong> - do not Disconnect and reconnect (Windows often drops
          the second connect). Only Connect if Session is idle or error.
        </p>
      ),
      do: (
        <div>
          {linked ? (
            <Callout variant="info" title="Session already open">
              Phase is <strong>{phase}</strong>. Skip Connect - go to step 2.
            </Callout>
          ) : (
            <ConnectBar hint="Soft-blue ADV first. Prefer TFT Reset BLE before a fresh Connect." />
          )}
        </div>
      ),
      checks: [{ id: "linked", label: "GATT session linked or live", pass: linked }],
    },
    {
      id: "notify",
      title: "Start notifications",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          This arms <strong>BS_TX</strong> notify (firmware <code>TX_EVT</code>) and applies a light
          hybrid <code>SENSOR_CFG_SET</code> so at least one <code>EVT_SENSOR</code> is published.
          You do <em>not</em> wait for POLICY/PING.
        </p>
      ),
      do: (
        <div>
          <div className="btn-row">
            <button
              className="primary"
              type="button"
              disabled={busy || phase === "connecting"}
              onClick={() => void startNotifications()}
            >
              {busy
                ? "Starting…"
                : phase === "live" && hasAny
                  ? "Notifications on"
                  : "Start notifications"}
            </button>
            <button type="button" disabled={busy} onClick={clearCounts}>
              Clear samples
            </button>
          </div>
          {actionError || lastError ? (
            <p className="err" style={{ marginTop: "0.65rem" }}>
              {actionError ?? lastError}
            </p>
          ) : null}
        </div>
      ),
      callout: (
        <Callout variant="warn" title="Connect fails on this chapter?">
          Do not hammer Connect. Press TFT <strong>Reset BLE</strong> (or hardware RESET) until
          soft-blue, keep the Chapter 03 session if it is still linked, then tap{" "}
          <strong>Start notifications</strong> once. Still stuck? Use the{" "}
          <Link to="/diag">/diag</Link> page.
        </Callout>
      ),
      checks: [
        { id: "live", label: "Session phase is live", pass: phase === "live" },
        {
          id: "evt",
          label: "At least one EVT_SENSOR decoded",
          pass: hasAny,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="04"
      title="Hear the first events"
      subtitle="Enable BS_TX notifications, apply hybrid CFG, and decode your first sensor events."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    >
      {hasAny ? (
        <div className="sensor-grid">
          {ALL_SENSOR_IDS.filter((id) => latest.has(id) || (counts.get(id) ?? 0) > 0).map((id) => (
            <SensorCard
              key={id}
              sensorId={id}
              sample={latest.get(id)}
              count={counts.get(id) ?? 0}
            />
          ))}
        </div>
      ) : null}
    </TutorialShell>
  );
}
