import { useState } from "react";
import {
  BMI270_FUSION_FEED_DEFAULT_MS,
  BMI270_MODE_HYBRID,
  BS_CMD_BMI270_FUSION_FEED_SET,
  BS_CMD_BMI270_MODE_SET,
  SENSOR_BMI270,
  SENSOR_BMM350,
  SENSOR_DPS368,
  SENSOR_SHT40,
  encodeBmi270FusionFeedSetBody,
  encodeBmi270ModeSetBody,
  teachingBmi270FusionCfg,
  teachingSensorCfg,
} from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { SensorCard } from "../../components/SensorCard";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

const IDS = [SENSOR_BMI270, SENSOR_BMM350, SENSOR_SHT40, SENSOR_DPS368] as const;

export function Lab07Page() {
  const { phase, goLive, applyCfgsFire, writeReqFire, latest, counts } = useBleSession();
  const [started, setStarted] = useState(false);
  const linked = phase === "linked" || phase === "live";
  const { prevPath, nextPath } = adjacentLabs("07");

  const startCards = async () => {
    if (phase !== "live") await goLive(400);
    await writeReqFire(BS_CMD_BMI270_MODE_SET, encodeBmi270ModeSetBody(BMI270_MODE_HYBRID));
    await writeReqFire(
      BS_CMD_BMI270_FUSION_FEED_SET,
      encodeBmi270FusionFeedSetBody(BMI270_FUSION_FEED_DEFAULT_MS),
    );
    await applyCfgsFire([
      teachingBmi270FusionCfg(200),
      teachingSensorCfg(SENSOR_BMM350),
      teachingSensorCfg(SENSOR_SHT40),
      teachingSensorCfg(SENSOR_DPS368),
    ]);
    setStarted(true);
  };

  const anyCard = IDS.some((id) => (counts.get(id) ?? 0) > 0 || latest.has(id));
  const allFour = IDS.every((id) => (counts.get(id) ?? 0) > 0);

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Motion and environment sensors share the same notify pipe. Connect, then enable the IMU
          hybrid mask plus env CFGs.
        </p>
      ),
      do: <ConnectBar />,
      checks: [{ id: "linked", label: "Session linked or live", pass: linked }],
    },
    {
      id: "cards",
      title: "Enable IMU + environment",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          BMI270 hybrid mode with mask <code>0x1f</code> fills accel/gyro/temp plus euler/quat.
          Mag + SHT40 + DPS368 use teaching CFG rates.
        </p>
      ),
      do: (
        <div className="btn-row">
          <button className="primary" type="button" disabled={!linked} onClick={() => void startCards()}>
            Go live + IMU / env cards
          </button>
        </div>
      ),
      callout: (
        <Callout variant="tip" title="Move the board">
          Tilt or rotate gently — BMI270 and BMM350 fields should change while env cards tick
          slowly.
        </Callout>
      ),
      checks: [
        { id: "started", label: "IMU/env CFGs applied", pass: started },
        { id: "any", label: "At least one of the four sensors published", pass: anyCard },
        { id: "all", label: "All four sensors published", pass: allFour },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="07"
      title="Motion + climate"
      subtitle="Read IMU, magnetometer, humidity, and pressure as live cards."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    >
      <div className="sensor-grid">
        {IDS.map((id) => (
          <SensorCard key={id} sensorId={id} sample={latest.get(id)} count={counts.get(id) ?? 0} />
        ))}
      </div>
    </TutorialShell>
  );
}
