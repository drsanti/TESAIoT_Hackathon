/** Locked GATT UUIDs — TESAIoT BS2 BLE peripheral */

export const BS2_BLE_SERVICE_UUID = "6f6b7a80-0001-4000-8000-00805f9b34fb";
export const BS2_BLE_CHAR_BS_RX_UUID = "6f6b7a80-0001-4001-8000-00805f9b34fb";
export const BS2_BLE_CHAR_BS_TX_UUID = "6f6b7a80-0001-4002-8000-00805f9b34fb";
export const BS2_BLE_CHAR_BS_LINK_UUID = "6f6b7a80-0001-4003-8000-00805f9b34fb";
export const BS2_BLE_CHAR_BS_CTRL_UUID = "6f6b7a80-0001-4004-8000-00805f9b34fb";

export const BS2_BLE_ADV_NAME_PREFIX = "TESAIoT-";

export function matchesBs2BlePeripheralName(localName: string | undefined | null): boolean {
  return typeof localName === "string" && localName.startsWith(BS2_BLE_ADV_NAME_PREFIX);
}
