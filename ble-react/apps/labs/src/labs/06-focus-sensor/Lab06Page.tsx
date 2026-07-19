import { useState } from "react";
import {
  ALL_SENSOR_IDS,
  SENSOR_NAMES,
  disabledSensorCfg,
  teachingSensorCfg,
} from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

export function Lab06Page() {
  const { phase, goLive, applyCfgsFire, counts, clearCounts } = useBleSession();
  const [focusId, setFocusId] = useState(2);
  const [status, setStatus] = useState("");
  const [applied, setApplied] = useState(false);
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("06");

  const applyFocus = async () => {
    setStatus("Applying CFG…");
    clearCounts();
    setApplied(false);
    if (phase !== "live") await goLive(400);
    const cfgs = ALL_SENSOR_IDS.map((id) =>
      id === focusId ? teachingSensorCfg(id) : disabledSensorCfg(id),
    );
    await applyCfgsFire(cfgs);
    setApplied(true);
    setStatus(`Focused ${SENSOR_NAMES[focusId]} — watch counts.`);
  };

  const others = ALL_SENSOR_IDS.filter((id) => id !== focusId).reduce(
    (n: number, id) => n + (counts.get(id) ?? 0),
    0,
  );
  const focusCount = counts.get(focusId) ?? 0;

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect & go live",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Configuration writes ride the same GATT session. Connect first; Apply focus will enable
          notifications if needed.
        </p>
      ),
      do: (
        <ConnectBar hint="SENSOR_CFG_SET is fire-and-forget (Write Command). Do not wait for RES." />
      ),
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "focus",
      title: "Focus one sensor",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Send a batch of <code>SENSOR_CFG_SET</code> bodies: enable the focus sensor, disable the
          others. Firmware applies without a blocking response — watch counters, not a RES wait.
        </p>
      ),
      do: (
        <div>
          <div className="select-row">
            <label htmlFor="focus">Sensor</label>
            <select
              id="focus"
              value={focusId}
              onChange={(e) => {
                setFocusId(Number(e.target.value));
                setApplied(false);
              }}
            >
              {ALL_SENSOR_IDS.map((id) => (
                <option key={id} value={id}>
                  {SENSOR_NAMES[id]}
                </option>
              ))}
            </select>
            <button className="primary" type="button" disabled={!linked} onClick={() => void applyFocus()}>
              Apply focus
            </button>
          </div>
          {status ? <p className="muted">{status}</p> : null}
          <ul className="checklist">
            {ALL_SENSOR_IDS.map((id) => (
              <li key={id}>
                {SENSOR_NAMES[id]}: <strong>{counts.get(id) ?? 0}</strong>
                {id === focusId ? " ← focus" : ""}
              </li>
            ))}
          </ul>
        </div>
      ),
      callout: (
        <Callout variant="info" title="Brief leftover ticks">
          Other sensors may tick briefly until CFG lands. After settle, only the focus id should
          climb.
        </Callout>
      ),
      checks: [
        { id: "applied", label: "Focus CFG applied", pass: applied },
        {
          id: "only",
          label: "Only the focused sensor is updating",
          pass: applied && focusCount > 0 && others === 0,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="06"
      title="Steer one sensor"
      subtitle="Use fire-and-forget SENSOR_CFG_SET to focus traffic on a single sensor."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    />
  );
}
