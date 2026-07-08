"""Locked GATT UUIDs — TESAIoT BS2 BLE peripheral."""

BS2_BLE_SERVICE_UUID = "6f6b7a80-0001-4000-8000-00805f9b34fb"
BS2_BLE_CHAR_BS_RX_UUID = "6f6b7a80-0001-4001-8000-00805f9b34fb"
BS2_BLE_CHAR_BS_TX_UUID = "6f6b7a80-0001-4002-8000-00805f9b34fb"
BS2_BLE_CHAR_BS_LINK_UUID = "6f6b7a80-0001-4003-8000-00805f9b34fb"

BS2_BLE_ADV_NAME_PREFIX = "TESAIoT-"


def matches_bs2_ble_name(local_name: str | None) -> bool:
    return isinstance(local_name, str) and local_name.startswith(BS2_BLE_ADV_NAME_PREFIX)
