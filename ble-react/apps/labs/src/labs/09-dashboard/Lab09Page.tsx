import { useState } from "react";
import { ALL_SENSOR_IDS, formatLinkSnapshot } from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { SensorCard } from "../../components/SensorCard";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";
import { goLiveAllSensorsHybrid } from "../goLiveAllHybrid";

export function Lab09Page() {
  const { phase, goLive, enableStreaming, applyCfgsFire, writeReqFire, latest, counts, link, readLink, logs } =
    useBleSession();
  const [started, setStarted] = useState(false);
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("09");

  const startBoard = async () => {
    await goLiveAllSensorsHybrid(
      { goLive, enableStreaming, writeReqFire, applyCfgsFire },
      { alreadyLive: phase === "live" },
    );
    try {
      await readLink();
    } catch {
      /* optional */
    }
    setStarted(true);
  };

  const liveCount = ALL_SENSOR_IDS.filter((id) => (counts.get(id) ?? 0) > 0).length;

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Compose everything you learned: connection chrome, six sensor cards, link status, and a
          short session log — the shape of a small live board.
        </p>
      ),
      do: <ConnectBar hint="Full live board: six sensors + link status." />,
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "board",
      title: "Start the live board",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          One action enables notify + hybrid CFGs for all sensors, then refreshes BS_LINK. Watch the
          grid fill and the log scroll.
        </p>
      ),
      do: (
        <div>
          <div className="btn-row">
            <button className="primary" type="button" disabled={!linked} onClick={() => void startBoard()}>
              Go live + all hybrid CFGs
            </button>
            <button type="button" disabled={!linked} onClick={() => void readLink()}>
              Refresh BS_LINK
            </button>
          </div>
          {link ? (
            <p className="muted" style={{ marginTop: "0.65rem" }}>
              Link: {formatLinkSnapshot(link)}
            </p>
          ) : null}
        </div>
      ),
      callout: (
        <Callout variant="info" title="Composition">
          This chapter is about layout and ops together — next you pick your own sensor set.
        </Callout>
      ),
      checks: [
        { id: "started", label: "Board started", pass: started },
        {
          id: "sensors",
          label: `At least four sensors publishing (${liveCount}/6)`,
          pass: liveCount >= 4,
        },
        { id: "link", label: "BS_LINK snapshot present", pass: link != null },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="09"
      title="Live board"
      subtitle="Compose connection, six cards, link status, and a session log."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    >
      <div className="sensor-grid">
        {ALL_SENSOR_IDS.map((id) => (
          <SensorCard key={id} sensorId={id} sample={latest.get(id)} count={counts.get(id) ?? 0} />
        ))}
      </div>
      <div className="panel">
        <h2>Session log</h2>
        <div className="log-box">{logs.slice(0, 20).join("\n") || "(empty)"}</div>
      </div>
    </TutorialShell>
  );
}
