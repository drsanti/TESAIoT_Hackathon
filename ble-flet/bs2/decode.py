"""EVT_SENSOR field decode — mirrors web-app shared/ble/decode/sensor-fields.js"""

from __future__ import annotations

import struct

SENSOR_KEYS = {
    0: "bmi270",
    1: "bmm350",
    2: "sht40",
    3: "dps368",
}

SENSOR_LABELS = {
    "bmi270": "BMI270",
    "bmm350": "BMM350",
    "sht40": "SHT40",
    "dps368": "DPS368",
}


def _read_i16(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated i16")
    return struct.unpack_from("<h", data, offset)[0], offset + 2


def _read_u16(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated u16")
    return struct.unpack_from("<H", data, offset)[0], offset + 2


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

    if mask & 0x01:
        if not take3(("accelX", "accelY", "accelZ")):
            return None
    if mask & 0x02:
        if not take3(("gyroX", "gyroY", "gyroZ")):
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


def map_sensor_sample(evt: dict) -> dict | None:
    sid = evt["sensor_id"]
    mask = evt["mask"] & 0xFF
    values = evt["values_bytes"]
    try:
        if sid == 0:
            fields = decode_bmi270(mask, values)
            if fields is None:
                return None
        elif sid == 1:
            fields = decode_bmm350(mask, values)
        elif sid == 2:
            fields = decode_sht40(mask, values)
        elif sid == 3:
            fields = decode_dps368(mask, values)
        else:
            return None
    except ValueError:
        return None
    if not fields:
        return None
    sensor = SENSOR_KEYS.get(sid)
    if sensor is None:
        return None
    return {
        "sensor": sensor,
        "sensor_id": sid,
        "label": SENSOR_LABELS[sensor],
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
    pub = cfg["publish_interval_ms"]
    samp = cfg["sampling_interval_ms"]
    if pub > 0 and pub < samp:
        cfg["publish_interval_ms"] = samp
    return cfg


def effective_publish_interval_ms(cfg: dict) -> int:
    pub = cfg.get("publish_interval_ms", 0)
    if pub > 0:
        return pub
    return cfg.get("sampling_interval_ms", 0)


def evt_cadence_interval_ms(cfg: dict) -> int:
    """Firmware periodic EVT spacing — limited by both sample and publish intervals."""
    mode = cfg.get("publish_mode", 0)
    samp = int(cfg.get("sampling_interval_ms", 0))
    pub = effective_publish_interval_ms(cfg)
    if mode == 1:
        return samp if samp > 0 else pub
    if samp <= 0:
        return pub
    if pub <= 0:
        return samp
    return max(samp, pub)


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


# Back-compat alias — Lab Quiet scene (1 Hz periodic all sensors).
from .scene_presets import get_scene_preset, scene_preset_sensor_cfgs  # noqa: E402

LAB_1HZ_SENSOR_CFGS: list[dict] = scene_preset_sensor_cfgs(get_scene_preset("labQuiet"))


def expected_cfg_hz(cfg: dict | None) -> float | None:
    """Expected periodic EVT rate from SENSOR_CFG, or None for off / on_change."""
    if not cfg or not cfg.get("enabled") or cfg.get("mask", 0) == 0:
        return None
    if int(cfg.get("publish_mode", 0)) == 1:
        return None
    ms = evt_cadence_interval_ms(cfg)
    if ms <= 0:
        return None
    return 1000.0 / ms


def format_configured_rate(cfg: dict | None) -> str:
    if not cfg or not cfg.get("enabled") or cfg.get("mask", 0) == 0:
        return "off"
    mode = cfg.get("publish_mode", 0)
    if mode == 1:
        return "on change"
    ms = evt_cadence_interval_ms(cfg)
    if ms <= 0:
        return "off"
    hz = 1000 / ms
    label = f"~{round(hz)} Hz" if hz >= 10 else f"~{hz:.1f} Hz"
    if mode == 2:
        return f"hybrid ≥{label}"
    pub = int(cfg.get("publish_interval_ms", 0))
    samp = int(cfg.get("sampling_interval_ms", 0))
    if pub > 0 and samp > 0 and pub != samp and max(samp, pub) == samp:
        pub_hz = 1000 / pub
        pub_l = f"~{round(pub_hz)} Hz" if pub_hz >= 10 else f"~{pub_hz:.1f} Hz"
        return f"{label} (pub {pub_l} ignored)"
    return label


def format_measured_rate(hz: float | None) -> str | None:
    if hz is None or hz <= 0:
        return None
    return f"~{round(hz)} Hz" if hz >= 10 else f"~{hz:.1f} Hz"


def rate_match_label(
    measured_hz: float | None,
    expected_hz: float | None,
    *,
    publish_mode: int = 0,
    tolerance: float = 0.25,
) -> str:
    """Compare measured deliver Hz to SENSOR_CFG expected cadence.

    - periodic (0): measured within ±tolerance of expected
    - on_change (1): not rate-checked (caller usually passes expected=None → n/a)
    - hybrid (2): expected is a *floor* (≥); OK when measured >= expected*(1-tolerance)
    """
    if expected_hz is None:
        return "n/a"
    if measured_hz is None or measured_hz <= 0:
        return "…"
    if publish_mode == 2:
        floor = expected_hz * (1.0 - tolerance)
        return "OK" if measured_hz >= floor else "MISMATCH"
    lo = expected_hz * (1.0 - tolerance)
    hi = expected_hz * (1.0 + tolerance)
    return "OK" if lo <= measured_hz <= hi else "MISMATCH"
