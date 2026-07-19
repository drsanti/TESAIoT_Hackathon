/** BS2 command IDs and BLE policy flags */

export const BS_CMD_PING = 0x01;
export const BS_CMD_SENSOR_CFG_GET = 0x10;
export const BS_CMD_SENSOR_CFG_SET = 0x11;
export const BS_CMD_BMI270_MODE_SET = 0x14;
export const BS_CMD_BMI270_MODE_GET = 0x15;
export const BS_CMD_BMI270_FUSION_FEED_SET = 0x16;
export const BS_CMD_BMI270_FUSION_FEED_GET = 0x17;
export const BS_CMD_BLE_POLICY_GET = 0x35;
export const BS_CMD_BLE_POLICY_SET = 0x36;

export const BLE_POLICY_FLAG_PERIPH_ADV = 0x01;
export const BLE_POLICY_FLAG_TX_EVT = 0x02;
export const BLE_POLICY_FLAG_RX_REQ = 0x04;

/** Boot default: advertise + accept REQ; no EVT until CCCD / POLICY. */
export const BLE_POLICY_BOOT_DEFAULT = 0x05;
/** Factory streaming: ADV + TX_EVT + RX_REQ */
export const BLE_POLICY_FACTORY_STREAMING = 0x07;

/** BMI270 stream modes (firmware bitstream_bmi270_runtime). */
export const BMI270_MODE_RAW = 0;
export const BMI270_MODE_FUSION = 1;
export const BMI270_MODE_HYBRID = 2;

export const BMI270_FUSION_FEED_DEFAULT_MS = 20;

export function encodeBmi270ModeSetBody(mode: number): Uint8Array {
  return Uint8Array.of(mode & 0xff);
}

export function encodeBmi270FusionFeedSetBody(intervalMs: number): Uint8Array {
  const out = new Uint8Array(2);
  new DataView(out.buffer).setUint16(0, intervalMs & 0xffff, true);
  return out;
}
