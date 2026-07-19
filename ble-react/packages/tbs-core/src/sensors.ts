/** Sensor IDs, names, default masks */

export const SENSOR_BMI270 = 0;
export const SENSOR_BMM350 = 1;
export const SENSOR_SHT40 = 2;
export const SENSOR_DPS368 = 3;
export const SENSOR_ADC_POT = 4;
export const SENSOR_SW_BTN = 5;

export type SensorId =
  | typeof SENSOR_BMI270
  | typeof SENSOR_BMM350
  | typeof SENSOR_SHT40
  | typeof SENSOR_DPS368
  | typeof SENSOR_ADC_POT
  | typeof SENSOR_SW_BTN;

export const SENSOR_NAMES: Record<number, string> = {
  [SENSOR_BMI270]: "BMI270",
  [SENSOR_BMM350]: "BMM350",
  [SENSOR_SHT40]: "SHT40",
  [SENSOR_DPS368]: "DPS368",
  [SENSOR_ADC_POT]: "ADC_POT",
  [SENSOR_SW_BTN]: "SW_BTN",
};

export const DEFAULT_MASKS: Record<number, number> = {
  [SENSOR_BMI270]: 0x03,
  [SENSOR_BMM350]: 0x03,
  [SENSOR_SHT40]: 0x03,
  [SENSOR_DPS368]: 0x03,
  [SENSOR_ADC_POT]: 0x0f,
  [SENSOR_SW_BTN]: 0x07,
};

/** BMI270 EVT mask bits (firmware BITSTREAM_BMI270_BS_MASK_*). */
export const BMI270_MASK_ACC = 0x01;
export const BMI270_MASK_GYR = 0x02;
export const BMI270_MASK_TMP = 0x04;
export const BMI270_MASK_EULER = 0x08;
export const BMI270_MASK_QUAT = 0x10;
/** Accel+gyro+temp+euler+quat */
export const BMI270_MASK_ALL = 0x1f;

export const ALL_SENSOR_IDS = [0, 1, 2, 3, 4, 5] as const;

export const ADC_POT_MASK = { POT1: 0x01, POT2: 0x02, POT3: 0x04, POT4: 0x08, ALL: 0x0f };
export const SW_BTN_MASK = { BTN0: 0x01, BTN1: 0x02, BTN2: 0x04, ALL: 0x07 };

/** SENSOR_CFG publishMode */
export const PUBLISH_MODE_PERIODIC = 0;
export const PUBLISH_MODE_ON_CHANGE = 1;
export const PUBLISH_MODE_HYBRID = 2;

export const TEACHING_PERIODIC_MS = 1000;
export const TEACHING_ADC_SAMPLE_MS = 50;
export const TEACHING_ADC_DELTA_MV = 10;
export const TEACHING_ADC_MIN_PUB_MS = 50;
export const TEACHING_BTN_SAMPLE_MS = 20;
export const TEACHING_HMI_PERIODIC_MS = 500;
