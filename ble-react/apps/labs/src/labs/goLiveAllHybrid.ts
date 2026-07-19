/**
 * Shared “go live + enable all hybrid sensors” helper for labs / dashboard.
 * Prefers enableStreaming (CCCD + POLICY 0x07 heal) when the session supports it.
 *
 * Applies IMU/env CFG first, then ADC_POT/SW_BTN (and re-applies user-IO once)
 * so BLE TX flood from BMI270 does not prevent pot/button CFG from sticking.
 */
import {
  BMI270_FUSION_FEED_DEFAULT_MS,
  BMI270_MODE_HYBRID,
  BS_CMD_BMI270_FUSION_FEED_SET,
  BS_CMD_BMI270_MODE_SET,
  encodeBmi270FusionFeedSetBody,
  encodeBmi270ModeSetBody,
  SENSOR_ADC_POT,
  SENSOR_SW_BTN,
  teachingHybridSensorCfgs,
  type SensorCfg,
} from "@ternion/tbs-core";

type HybridSession = {
  goLive: (settleMs?: number) => Promise<void>;
  enableStreaming?: (opts?: { settleMs?: number; policyTimeoutMs?: number }) => Promise<void>;
  writeReqFire: (cmdId: number, body?: Uint8Array) => Promise<void>;
  applyCfgsFire: (cfgs: SensorCfg[], gapMs?: number) => Promise<void>;
};

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function goLiveAllSensorsHybrid(
  session: HybridSession,
  opts: { alreadyLive?: boolean } = {},
): Promise<void> {
  if (session.enableStreaming) {
    await session.enableStreaming({ settleMs: opts.alreadyLive ? 50 : 400 });
  } else if (!opts.alreadyLive) {
    await session.goLive(400);
  }
  await session.writeReqFire(BS_CMD_BMI270_MODE_SET, encodeBmi270ModeSetBody(BMI270_MODE_HYBRID));
  await session.writeReqFire(
    BS_CMD_BMI270_FUSION_FEED_SET,
    encodeBmi270FusionFeedSetBody(BMI270_FUSION_FEED_DEFAULT_MS),
  );

  const all = teachingHybridSensorCfgs();
  const imuEnv = all.filter((c) => c.sensorId !== SENSOR_ADC_POT && c.sensorId !== SENSOR_SW_BTN);
  const userIo = all.filter((c) => c.sensorId === SENSOR_ADC_POT || c.sensorId === SENSOR_SW_BTN);

  await session.applyCfgsFire(imuEnv, 60);
  await session.applyCfgsFire(userIo, 100);
  // Re-arm pot/button hybrid gate after IMU CFG storm (mirrors UART live dump).
  await sleep(120);
  await session.applyCfgsFire(userIo, 100);
}
