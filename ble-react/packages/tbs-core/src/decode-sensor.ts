import type { EvtSensorRaw } from "./wire.js";
import {
  ADC_POT_MASK,
  SENSOR_ADC_POT,
  SENSOR_BMI270,
  SENSOR_BMM350,
  SENSOR_DPS368,
  SENSOR_NAMES,
  SENSOR_SHT40,
  SENSOR_SW_BTN,
  SW_BTN_MASK,
} from "./sensors.js";

export type SensorSample = {
  sensorId: number;
  label: string;
  counter: number;
  deviceMs: number;
  mask: number;
  fields: Record<string, number>;
};

function readI16(data: Uint8Array, offset: number): [number, number] {
  if (offset + 2 > data.byteLength) throw new Error("truncated i16");
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  return [view.getInt16(offset, true), offset + 2];
}

function readU16(data: Uint8Array, offset: number): [number, number] {
  if (offset + 2 > data.byteLength) throw new Error("truncated u16");
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  return [view.getUint16(offset, true), offset + 2];
}

function readU32(data: Uint8Array, offset: number): [number, number] {
  if (offset + 4 > data.byteLength) throw new Error("truncated u32");
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  return [view.getUint32(offset, true), offset + 4];
}

function scale(v: number, div: number): number {
  return v / div;
}

function decodeBmi270(mask: number, values: Uint8Array): Record<string, number> | null {
  let o = 0;
  const fields: Record<string, number> = {};

  const take3 = (keys: [string, string, string]): boolean => {
    if (o + 6 > values.byteLength) return false;
    let a: number;
    let b: number;
    let c: number;
    [a, o] = readI16(values, o);
    [b, o] = readI16(values, o);
    [c, o] = readI16(values, o);
    fields[keys[0]] = scale(a, 100);
    fields[keys[1]] = scale(b, 100);
    fields[keys[2]] = scale(c, 100);
    return true;
  };

  if (mask & 0x01 && !take3(["accelX", "accelY", "accelZ"])) return null;
  if (mask & 0x02 && !take3(["gyroX", "gyroY", "gyroZ"])) return null;
  if (mask & 0x04) {
    if (o + 2 > values.byteLength) return null;
    let t: number;
    [t, o] = readI16(values, o);
    fields.temperatureC = scale(t, 100);
  }
  if (mask & 0x08) {
    if (o + 6 > values.byteLength) return null;
    let h: number;
    let p: number;
    let r: number;
    [h, o] = readI16(values, o);
    [p, o] = readI16(values, o);
    [r, o] = readI16(values, o);
    fields.headingRad = scale(h, 100);
    fields.pitchRad = scale(p, 100);
    fields.rollRad = scale(r, 100);
  }
  if (mask & 0x10) {
    if (o + 8 > values.byteLength) return null;
    let qw: number;
    let qx: number;
    let qy: number;
    let qz: number;
    [qw, o] = readU16(values, o);
    [qx, o] = readI16(values, o);
    [qy, o] = readI16(values, o);
    [qz, o] = readI16(values, o);
    fields.quatW = scale(qw, 10000);
    fields.quatX = scale(qx, 10000);
    fields.quatY = scale(qy, 10000);
    fields.quatZ = scale(qz, 10000);
  }
  if (o !== values.byteLength) return null;
  return Object.keys(fields).length ? fields : null;
}

function decodeBmm350(mask: number, values: Uint8Array): Record<string, number> {
  let o = 0;
  const fields: Record<string, number> = {};
  if (mask & 0x01) {
    let mx: number;
    let my: number;
    let mz: number;
    [mx, o] = readI16(values, o);
    [my, o] = readI16(values, o);
    [mz, o] = readI16(values, o);
    fields.magX = scale(mx, 100);
    fields.magY = scale(my, 100);
    fields.magZ = scale(mz, 100);
  }
  if (mask & 0x02) {
    let t: number;
    [t, o] = readI16(values, o);
    fields.temperatureC = scale(t, 100);
  }
  return fields;
}

function decodeSht40(mask: number, values: Uint8Array): Record<string, number> {
  let o = 0;
  const fields: Record<string, number> = {};
  if (mask & 0x01) {
    let t: number;
    [t, o] = readI16(values, o);
    fields.temperatureC = scale(t, 100);
  }
  if (mask & 0x02) {
    let h: number;
    [h, o] = readI16(values, o);
    fields.humidityPct = scale(h, 100);
  }
  return fields;
}

function decodeDps368(mask: number, values: Uint8Array): Record<string, number> {
  let o = 0;
  const fields: Record<string, number> = {};
  if (mask & 0x01) {
    let p: number;
    [p, o] = readI16(values, o);
    fields.pressureHpa = scale(p, 10);
  }
  if (mask & 0x02) {
    let t: number;
    [t, o] = readI16(values, o);
    fields.temperatureC = scale(t, 100);
  }
  return fields;
}

function decodeAdcPot(mask: number, values: Uint8Array): Record<string, number> | null {
  let o = 0;
  const fields: Record<string, number> = {};
  for (const [bit, key] of [
    [ADC_POT_MASK.POT1, "pot1_mv"],
    [ADC_POT_MASK.POT2, "pot2_mv"],
    [ADC_POT_MASK.POT3, "pot3_mv"],
    [ADC_POT_MASK.POT4, "pot4_mv"],
  ] as const) {
    if (mask & bit) {
      if (o + 2 > values.byteLength) return null;
      let v: number;
      [v, o] = readI16(values, o);
      fields[key] = v;
    }
  }
  if (o !== values.byteLength) return null;
  return Object.keys(fields).length ? fields : null;
}

function decodeSwBtn(mask: number, values: Uint8Array): Record<string, number> | null {
  if (values.byteLength < 1) return null;
  let o = 1;
  const fields: Record<string, number> = { state: values[0]! };
  for (const [bit, key] of [
    [SW_BTN_MASK.BTN0, "btn0_count"],
    [SW_BTN_MASK.BTN1, "btn1_count"],
    [SW_BTN_MASK.BTN2, "btn2_count"],
  ] as const) {
    if (mask & bit) {
      if (o + 4 > values.byteLength) return null;
      let c: number;
      [c, o] = readU32(values, o);
      fields[key] = c;
    }
  }
  if (o !== values.byteLength) return null;
  return fields;
}

export function mapSensorSample(evt: EvtSensorRaw): SensorSample | null {
  const sid = evt.sensorId;
  const mask = evt.mask & 0xff;
  const values = evt.values;
  let fields: Record<string, number> | null;
  try {
    if (sid === SENSOR_BMI270) fields = decodeBmi270(mask, values);
    else if (sid === SENSOR_BMM350) fields = decodeBmm350(mask, values);
    else if (sid === SENSOR_SHT40) fields = decodeSht40(mask, values);
    else if (sid === SENSOR_DPS368) fields = decodeDps368(mask, values);
    else if (sid === SENSOR_ADC_POT) fields = decodeAdcPot(mask, values);
    else if (sid === SENSOR_SW_BTN) fields = decodeSwBtn(mask, values);
    else return null;
  } catch {
    return null;
  }
  if (!fields || Object.keys(fields).length === 0) return null;
  return {
    sensorId: sid,
    label: SENSOR_NAMES[sid] ?? `id=${sid}`,
    counter: evt.counter,
    deviceMs: evt.deviceMs,
    mask,
    fields,
  };
}

export function formatSwBtnState(state: number): string {
  const bits: string[] = [];
  if (state & SW_BTN_MASK.BTN0) bits.push("BTN0");
  if (state & SW_BTN_MASK.BTN1) bits.push("BTN1");
  if (state & SW_BTN_MASK.BTN2) bits.push("BTN2");
  return bits.length ? bits.join("+") : "(none)";
}
