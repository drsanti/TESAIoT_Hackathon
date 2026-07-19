import { useState } from "react";
import { SENSOR_ADC_POT, SENSOR_SW_BTN, teachingSensorCfg } from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { SensorCard } from "../../components/SensorCard";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

export function Lab08Page() {
  const { phase, goLive, applyCfgsFire, latest, counts } = useBleSession();
  const [enabled, setEnabled] = useState(false);
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("08");

  const enableHmi = async () => {
    if (phase !== "live") await goLive(400);
    await applyCfgsFire([teachingSensorCfg(SENSOR_ADC_POT), teachingSensorCfg(SENSOR_SW_BTN)]);
    setEnabled(true);
  };

  const potOk = (counts.get(SENSOR_ADC_POT) ?? 0) > 0;
  const btnOk = (counts.get(SENSOR_SW_BTN) ?? 0) > 0;

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          On-board pots and buttons publish as sensors <code>ADC_POT</code> and{" "}
          <code>SW_BTN</code>. Connect first.
        </p>
      ),
      do: <ConnectBar hint="Hybrid also publishes periodically — turn a pot or press a button for on-change." />,
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "hmi",
      title: "Enable pots & buttons",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Apply teaching CFG for both HMI sensors. Values show as millivolts / button state and
          press counts on the cards below.
        </p>
      ),
      do: (
        <div className="btn-row">
          <button className="primary" type="button" disabled={!linked} onClick={() => void enableHmi()}>
            Enable ADC_POT + SW_BTN
          </button>
        </div>
      ),
      callout: (
        <Callout variant="tip" title="Try it">
          Turn a potentiometer and press a user button on the DevKit while watching the cards.
        </Callout>
      ),
      checks: [
        { id: "en", label: "HMI CFGs applied", pass: enabled },
        { id: "pot", label: "ADC_POT published", pass: potOk },
        { id: "btn", label: "SW_BTN published", pass: btnOk },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="08"
      title="Knobs and buttons"
      subtitle="Stream on-board potentiometers and switches."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    >
      <div className="sensor-grid">
        <SensorCard
          sensorId={SENSOR_ADC_POT}
          sample={latest.get(SENSOR_ADC_POT)}
          count={counts.get(SENSOR_ADC_POT) ?? 0}
        />
        <SensorCard
          sensorId={SENSOR_SW_BTN}
          sample={latest.get(SENSOR_SW_BTN)}
          count={counts.get(SENSOR_SW_BTN) ?? 0}
        />
      </div>
    </TutorialShell>
  );
}
