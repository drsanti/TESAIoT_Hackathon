import {
  DEFAULT_MASKS,
  TEACHING_ADC_DELTA_MV,
  SENSOR_ADC_POT,
  SENSOR_BMI270,
  SENSOR_BMM350,
  SENSOR_DPS368,
  SENSOR_SHT40,
  SENSOR_SW_BTN,
  ALL_SENSOR_IDS,
  BMI270_MASK_ALL,
  PUBLISH_MODE_HYBRID,
} from "./sensors.js";

export type SensorCfg = {
  sensorId: number;
  enabled: boolean;
  publishMode: number;
  mask: number;
  samplingIntervalMs: number;
  deltaX100: number;
  minPublishIntervalMs: number;
  publishIntervalMs: number;
};

/**
 * Teaching hybrid rates (SENSOR_CFG_V2 Motion-style), tuned for BLE TX:
 * publishMode=2 → periodic OR on_change. Keep IMU ≤5 Hz so ATT notifies do not
 * starve ADC_POT / SW_BTN (bridge TX queue drops stream EVT under flood).
 */
const HYBRID_TEACHING: Record<
  number,
  {
    mask: number;
    samplingIntervalMs: number;
    publishIntervalMs: number;
    deltaX100: number;
    minPublishIntervalMs: number;
  }
> = {
  [SENSOR_BMI270]: {
    mask: BMI270_MASK_ALL,
    samplingIntervalMs: 100,
    publishIntervalMs: 200,
    deltaX100: 10,
    minPublishIntervalMs: 100,
  },
  [SENSOR_BMM350]: {
    mask: DEFAULT_MASKS[SENSOR_BMM350]!,
    samplingIntervalMs: 100,
    publishIntervalMs: 200,
    deltaX100: 10,
    minPublishIntervalMs: 100,
  },
  [SENSOR_SHT40]: {
    mask: DEFAULT_MASKS[SENSOR_SHT40]!,
    samplingIntervalMs: 250,
    publishIntervalMs: 500,
    deltaX100: 5,
    minPublishIntervalMs: 250,
  },
  [SENSOR_DPS368]: {
    mask: DEFAULT_MASKS[SENSOR_DPS368]!,
    samplingIntervalMs: 500,
    publishIntervalMs: 1000,
    deltaX100: 5,
    minPublishIntervalMs: 500,
  },
  [SENSOR_ADC_POT]: {
    mask: DEFAULT_MASKS[SENSOR_ADC_POT]!,
    samplingIntervalMs: 50,
    publishIntervalMs: 200,
    deltaX100: TEACHING_ADC_DELTA_MV,
    minPublishIntervalMs: 50,
  },
  [SENSOR_SW_BTN]: {
    mask: DEFAULT_MASKS[SENSOR_SW_BTN]!,
    samplingIntervalMs: 50,
    publishIntervalMs: 250,
    deltaX100: 0,
    minPublishIntervalMs: 50,
  },
};

export function encodeSensorCfgBody(cfg: SensorCfg): Uint8Array {
  const body = new Uint8Array(12);
  let samp = cfg.samplingIntervalMs | 0;
  let pub = cfg.publishIntervalMs | 0;
  if (pub > 0 && pub < samp) pub = samp;
  body[0] = cfg.sensorId & 0xff;
  body[1] = cfg.enabled ? 1 : 0;
  body[2] = cfg.publishMode & 0xff;
  body[3] = cfg.mask & 0xff;
  const view = new DataView(body.buffer);
  view.setUint16(4, samp, true);
  view.setUint16(6, cfg.deltaX100 | 0, true);
  view.setUint16(8, cfg.minPublishIntervalMs | 0, true);
  view.setUint16(10, pub, true);
  return body;
}

export function decodeSensorCfgBody(body: Uint8Array): SensorCfg | null {
  if (body.byteLength < 7) return null;
  const view = new DataView(body.buffer, body.byteOffset, body.byteLength);
  const cfg: SensorCfg = {
    sensorId: body[0]!,
    enabled: body[1] !== 0,
    publishMode: body.byteLength > 2 ? body[2]! : 0,
    mask: body.byteLength > 3 ? body[3]! : 0,
    samplingIntervalMs: body.byteLength >= 6 ? view.getUint16(4, true) : 0,
    deltaX100: 0,
    minPublishIntervalMs: 0,
    publishIntervalMs: 0,
  };
  if (body.byteLength >= 10) {
    cfg.deltaX100 = view.getUint16(6, true);
    cfg.minPublishIntervalMs = view.getUint16(8, true);
  }
  if (body.byteLength >= 12) {
    cfg.publishIntervalMs = view.getUint16(10, true);
  }
  return cfg;
}

/** Default teaching CFG = hybrid publish for every sensor (incl. pots/buttons). */
export function teachingSensorCfg(sensorId: number): SensorCfg {
  return teachingHybridSensorCfg(sensorId);
}

/** Hybrid SENSOR_CFG for one sensor (publishMode=2). BMI270 uses full mask 0x1f. */
export function teachingHybridSensorCfg(sensorId: number): SensorCfg {
  const sid = sensorId | 0;
  const rates = HYBRID_TEACHING[sid] ?? {
    mask: DEFAULT_MASKS[sid] ?? 0,
    samplingIntervalMs: 1000,
    publishIntervalMs: 1000,
    deltaX100: 0,
    minPublishIntervalMs: 0,
  };
  return {
    sensorId: sid,
    enabled: true,
    publishMode: PUBLISH_MODE_HYBRID,
    mask: rates.mask,
    samplingIntervalMs: rates.samplingIntervalMs,
    deltaX100: rates.deltaX100,
    minPublishIntervalMs: rates.minPublishIntervalMs,
    publishIntervalMs: rates.publishIntervalMs,
  };
}

/** BMI270 hybrid CFG with euler+quat mask — pair with BMI270_MODE_SET hybrid. */
export function teachingBmi270FusionCfg(_periodMs?: number): SensorCfg {
  return teachingHybridSensorCfg(SENSOR_BMI270);
}

export function teachingSensorCfgs(): SensorCfg[] {
  return teachingHybridSensorCfgs();
}

export function teachingHybridSensorCfgs(): SensorCfg[] {
  return ALL_SENSOR_IDS.map((id) => teachingHybridSensorCfg(id));
}

export function disabledSensorCfg(sensorId: number): SensorCfg {
  return {
    sensorId,
    enabled: false,
    publishMode: 0,
    mask: 0,
    samplingIntervalMs: 1000,
    deltaX100: 0,
    minPublishIntervalMs: 0,
    publishIntervalMs: 0,
  };
}
