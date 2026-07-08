"""ATT chunk envelope v1 — mirrors packages/bitstream-ble-client/src/chunk.ts"""

from __future__ import annotations

BS2_BLE_CHUNK_VER = 1
BS2_BLE_CHUNK_FLAG_EOR = 0x01
BS2_BLE_CHUNK_HEADER_LEN = 6


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
