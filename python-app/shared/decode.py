"""EVT_SENSOR field decode — sensors 0–5 (teaching)."""

from __future__ import annotations

import struct

from .sensor_ids import (
    SENSOR_ADC_POT,
    SENSOR_BMI270,
    SENSOR_BMM350,
    SENSOR_DPS368,
    SENSOR_NAMES,
    SENSOR_SHT40,
    SENSOR_SW_BTN,
    ADC_POT_MASK,
    SW_BTN_MASK,
)


def _read_i16(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated i16")
    return struct.unpack_from("<h", data, offset)[0], offset + 2


def _read_u16(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated u16")
    return struct.unpack_from("<H", data, offset)[0], offset + 2


def _read_u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated u32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _scale(v: int, scale: int) -> float:
    return v / scale


def decode_bmi270(mask: int, values: bytes) -> dict[str, float] | None:
    o = 0
    fields: dict[str, float] = {}

    def take3(keys: tuple[str, str, str]) -> bool:
        nonlocal o
        if o + 6 > len(values):
            return False
        ax, o = _read_i16(values, o)
        ay, o = _read_i16(values, o)
        az, o = _read_i16(values, o)
        fields[keys[0]] = _scale(ax, 100)
        fields[keys[1]] = _scale(ay, 100)
        fields[keys[2]] = _scale(az, 100)
        return True

    if mask & 0x01 and not take3(("accelX", "accelY", "accelZ")):
        return None
    if mask & 0x02 and not take3(("gyroX", "gyroY", "gyroZ")):
        return None
    if mask & 0x04:
        if o + 2 > len(values):
            return None
        t, o = _read_i16(values, o)
        fields["temperatureC"] = _scale(t, 100)
    if mask & 0x08:
        if o + 6 > len(values):
            return None
        h, o = _read_i16(values, o)
        p, o = _read_i16(values, o)
        r, o = _read_i16(values, o)
        fields["headingRad"] = _scale(h, 100)
        fields["pitchRad"] = _scale(p, 100)
        fields["rollRad"] = _scale(r, 100)
    if mask & 0x10:
        if o + 8 > len(values):
            return None
        qw, o = _read_u16(values, o)
        qx, o = _read_i16(values, o)
        qy, o = _read_i16(values, o)
        qz, o = _read_i16(values, o)
        fields["quatW"] = _scale(qw, 10000)
        fields["quatX"] = _scale(qx, 10000)
        fields["quatY"] = _scale(qy, 10000)
        fields["quatZ"] = _scale(qz, 10000)
    if o != len(values):
        return None
    return fields if fields else None


def decode_bmm350(mask: int, values: bytes) -> dict[str, float]:
    o = 0
    fields: dict[str, float] = {}
    if mask & 0x01:
        mx, o = _read_i16(values, o)
        my, o = _read_i16(values, o)
        mz, o = _read_i16(values, o)
        fields["magX"] = _scale(mx, 100)
        fields["magY"] = _scale(my, 100)
        fields["magZ"] = _scale(mz, 100)
    if mask & 0x02:
        t, o = _read_i16(values, o)
        fields["temperatureC"] = _scale(t, 100)
    return fields


def decode_sht40(mask: int, values: bytes) -> dict[str, float]:
    o = 0
    fields: dict[str, float] = {}
    if mask & 0x01:
        t, o = _read_i16(values, o)
        fields["temperatureC"] = _scale(t, 100)
    if mask & 0x02:
        h, o = _read_i16(values, o)
        fields["humidityPct"] = _scale(h, 100)
    return fields


def decode_dps368(mask: int, values: bytes) -> dict[str, float]:
    o = 0
    fields: dict[str, float] = {}
    if mask & 0x01:
        p, o = _read_i16(values, o)
        fields["pressureHpa"] = _scale(p, 10)
    if mask & 0x02:
        t, o = _read_i16(values, o)
        fields["temperatureC"] = _scale(t, 100)
    return fields


def decode_adc_pot(mask: int, values: bytes) -> dict[str, int] | None:
    o = 0
    fields: dict[str, int] = {}
    for bit, key in (
        (ADC_POT_MASK["POT1"], "pot1_mv"),
        (ADC_POT_MASK["POT2"], "pot2_mv"),
        (ADC_POT_MASK["POT3"], "pot3_mv"),
        (ADC_POT_MASK["POT4"], "pot4_mv"),
    ):
        if mask & bit:
            if o + 2 > len(values):
                return None
            v, o = _read_i16(values, o)
            fields[key] = v
    if o != len(values):
        return None
    return fields if fields else None


def decode_sw_btn(mask: int, values: bytes) -> dict[str, int] | None:
    if len(values) < 1:
        return None
    o = 1
    fields: dict[str, int] = {"state": values[0]}
    for bit, key in (
        (SW_BTN_MASK["BTN0"], "btn0_count"),
        (SW_BTN_MASK["BTN1"], "btn1_count"),
        (SW_BTN_MASK["BTN2"], "btn2_count"),
    ):
        if mask & bit:
            if o + 4 > len(values):
                return None
            c, o = _read_u32(values, o)
            fields[key] = c
    if o != len(values):
        return None
    return fields


def map_sensor_sample(evt: dict) -> dict | None:
    sid = evt["sensor_id"]
    mask = evt["mask"] & 0xFF
    values = evt["values_bytes"]
    try:
        if sid == SENSOR_BMI270:
            fields = decode_bmi270(mask, values)
        elif sid == SENSOR_BMM350:
            fields = decode_bmm350(mask, values)
        elif sid == SENSOR_SHT40:
            fields = decode_sht40(mask, values)
        elif sid == SENSOR_DPS368:
            fields = decode_dps368(mask, values)
        elif sid == SENSOR_ADC_POT:
            fields = decode_adc_pot(mask, values)
        elif sid == SENSOR_SW_BTN:
            fields = decode_sw_btn(mask, values)
        else:
            return None
    except ValueError:
        return None
    if not fields:
        return None
    return {
        "sensor_id": sid,
        "label": SENSOR_NAMES.get(sid, f"id={sid}"),
        "counter": evt["counter"],
        "device_ms": evt["device_ms"],
        "mask": mask,
        "fields": fields,
    }


def decode_sensor_cfg_body(body: bytes) -> dict | None:
    if len(body) < 7:
        return None
    cfg = {
        "sensor_id": body[0],
        "enabled": body[1] != 0,
        "publish_mode": body[2] if len(body) > 2 else 0,
        "mask": body[3] if len(body) > 3 else 0,
        "sampling_interval_ms": body[4] | (body[5] << 8) if len(body) >= 6 else 0,
        "delta_x100": 0,
        "min_publish_interval_ms": 0,
        "publish_interval_ms": 0,
    }
    if len(body) >= 10:
        cfg["delta_x100"] = body[6] | (body[7] << 8)
        cfg["min_publish_interval_ms"] = body[8] | (body[9] << 8)
    if len(body) >= 12:
        cfg["publish_interval_ms"] = body[10] | (body[11] << 8)
    return cfg


def encode_sensor_cfg_body(cfg: dict) -> bytes:
    body = bytearray(12)
    samp = int(cfg.get("sampling_interval_ms", 1000))
    pub = int(cfg.get("publish_interval_ms", 0))
    if pub > 0 and pub < samp:
        pub = samp
    body[0] = int(cfg["sensor_id"]) & 0xFF
    body[1] = 1 if cfg.get("enabled", True) else 0
    body[2] = int(cfg.get("publish_mode", 0)) & 0xFF
    body[3] = int(cfg.get("mask", 0)) & 0xFF
    struct.pack_into("<H", body, 4, samp)
    struct.pack_into("<H", body, 6, int(cfg.get("delta_x100", 0)))
    struct.pack_into("<H", body, 8, int(cfg.get("min_publish_interval_ms", 0)))
    struct.pack_into("<H", body, 10, pub)
    return bytes(body)


def format_sw_btn_state(state: int) -> str:
    bits = []
    if state & SW_BTN_MASK["BTN0"]:
        bits.append("BTN0")
    if state & SW_BTN_MASK["BTN1"]:
        bits.append("BTN1")
    if state & SW_BTN_MASK["BTN2"]:
        bits.append("BTN2")
    return "+".join(bits) if bits else "(none)"
