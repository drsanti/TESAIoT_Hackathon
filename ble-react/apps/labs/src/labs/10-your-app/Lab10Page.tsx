import { useState } from "react";
import {
  ALL_SENSOR_IDS,
  SENSOR_NAMES,
  teachingSensorCfg,
  type SensorId,
} from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { SensorCard } from "../../components/SensorCard";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

/**
 * Lab 10 — forkable scaffold. Students edit `selected` to change the sensor set.
 */
export function Lab10Page() {
  const [selected, setSelected] = useState<number[]>([0, 2, 4]);
  const [ran, setRan] = useState(false);
  const { phase, goLive, applyCfgsFire, latest, counts } = useBleSession();
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("10");

  const toggle = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    setRan(false);
  };

  const run = async () => {
    if (phase !== "live") await goLive(400);
    await applyCfgsFire(selected.map((id) => teachingSensorCfg(id)));
    setRan(true);
  };

  const anySelectedLive = selected.some((id) => (counts.get(id) ?? 0) > 0);

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          You now own the sensor set. Same hooks as <code>apps/dashboard</code> — Connect, pick
          sensors, go live.
        </p>
      ),
      do: (
        <ConnectBar hint="Edit the checklist (or this page’s code) — same session APIs as the dashboard app." />
      ),
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "scaffold",
      title: "Choose sensors & run",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Toggle which sensors to enable, then apply teaching CFG for that set. Fork this page or
          open the dashboard demo when you want a polished consumer shell.
        </p>
      ),
      do: (
        <div>
          <div className="btn-row">
            {ALL_SENSOR_IDS.map((id) => (
              <button
                key={id}
                type="button"
                className={selected.includes(id) ? "primary" : undefined}
                onClick={() => toggle(id)}
              >
                {SENSOR_NAMES[id]}
              </button>
            ))}
          </div>
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button
              className="primary"
              type="button"
              disabled={!linked || selected.length === 0}
              onClick={() => void run()}
            >
              Go live + apply selected
            </button>
          </div>
        </div>
      ),
      callout: (
        <Callout variant="tip" title="Graduate">
          Next: <code>pnpm dev:dashboard</code> → <code>http://localhost:5175</code> for the
          polished Connect / Live / Link / Log shell.
        </Callout>
      ),
      checks: [
        {
          id: "pick",
          label: "At least one sensor selected",
          pass: selected.length > 0,
        },
        { id: "ran", label: "Selected CFGs applied", pass: ran },
        {
          id: "live",
          label: "At least one selected sensor published",
          pass: anySelectedLive,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="10"
      title="Your scaffold"
      subtitle="Build a minimal app from the same Web Bluetooth session hooks."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    >
      <div className="sensor-grid">
        {selected.map((id) => (
          <SensorCard
            key={id}
            sensorId={id as SensorId}
            sample={latest.get(id)}
            count={counts.get(id) ?? 0}
          />
        ))}
      </div>
    </TutorialShell>
  );
}
