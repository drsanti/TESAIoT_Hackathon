"""BS2 wire + ATT chunk reassembly — teaching copies for the labs."""

from __future__ import annotations

BS_PREFIX = b"BS "
BS_TYPE_REQ = 0x02
BS_TYPE_RES = 0x03
BS_TYPE_EVT_SENSOR = 0x04

BS_CMD_PING = 0x01
BS_CMD_SENSOR_CFG_GET = 0x10
BS_CMD_SENSOR_CFG_SET = 0x11
BS_CMD_BLE_POLICY_GET = 0x35
BS_CMD_BLE_POLICY_SET = 0x36

BLE_POLICY_BOOT_DEFAULT = 0x05
BLE_POLICY_FACTORY_STREAMING = 0x07

BS2_BLE_CHUNK_VER = 1
BS2_BLE_CHUNK_FLAG_EOR = 0x01
BS2_BLE_CHUNK_HEADER_LEN = 6


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_bs_req(req_id: int, cmd_id: int, body: bytes = b"", flags: int = 0) -> bytes:
    payload = bytes((req_id & 0xFF, (req_id >> 8) & 0xFF, cmd_id & 0xFF, flags & 0xFF)) + body
    plen = len(payload)
    header = BS_PREFIX + bytes((plen & 0xFF, (plen >> 8) & 0xFF, BS_TYPE_REQ))
    crc = crc16_ccitt(header[3:] + payload)
    return header + payload + bytes((crc & 0xFF, (crc >> 8) & 0xFF, 0x0D, 0x0A))


def try_parse_bs2_frame(wire: bytes) -> tuple[int, bytes] | None:
    if len(wire) < 14 or wire[0:3] != BS_PREFIX:
        return None
    plen = wire[3] | (wire[4] << 8)
    needed = 3 + 2 + 1 + plen + 2 + 2
    if len(wire) < needed or wire[needed - 2 : needed] != b"\r\n":
        return None
    crc_expected = wire[6 + plen] | (wire[7 + plen] << 8)
    crc_actual = crc16_ccitt(wire[3 : 6 + plen])
    if crc_actual != crc_expected:
        return None
    return wire[5], wire[6 : 6 + plen]


def try_parse_bs2_res(wire: bytes) -> tuple[int, int, int, bytes] | None:
    parsed = try_parse_bs2_frame(wire)
    if parsed is None:
        return None
    msg_type, payload = parsed
    if msg_type != BS_TYPE_RES or len(payload) < 4:
        return None
    req_id = payload[0] | (payload[1] << 8)
    cmd_id = payload[2]
    status = payload[3]
    body = payload[4:]
    return req_id, cmd_id, status, body


def try_parse_evt_sensor(wire: bytes) -> dict | None:
    parsed = try_parse_bs2_frame(wire)
    if parsed is None:
        return None
    msg_type, payload = parsed
    if msg_type != BS_TYPE_EVT_SENSOR or len(payload) < 10:
        return None
    return {
        "sensor_id": payload[0],
        "mask": payload[1],
        "counter": int.from_bytes(payload[2:6], "little"),
        "device_ms": int.from_bytes(payload[6:10], "little"),
        "values_bytes": payload[10:],
    }


class Bs2BleChunkReassembler:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._pending: list[bytes | None] = []
        self._expected_total = 0
        self._active_seq = -1

    def feed(self, chunk: bytes) -> bytes | None:
        if len(chunk) < BS2_BLE_CHUNK_HEADER_LEN or chunk[0] != BS2_BLE_CHUNK_VER:
            self.reset()
            return None

        seq = chunk[2] | (chunk[3] << 8)
        idx = chunk[4]
        total = chunk[5]
        payload = chunk[BS2_BLE_CHUNK_HEADER_LEN:]

        if total < 1 or idx >= total:
            self.reset()
            return None

        if seq != self._active_seq or total != self._expected_total:
            self._pending = [None] * total
            self._active_seq = seq
            self._expected_total = total

        self._pending[idx] = payload

        if (chunk[1] & BS2_BLE_CHUNK_FLAG_EOR) == 0:
            return None

        if any(part is None for part in self._pending):
            self.reset()
            return None

        frame = b"".join(part for part in self._pending if part is not None)
        self.reset()
        return frame
