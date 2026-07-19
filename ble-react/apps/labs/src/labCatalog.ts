export const LAB_CATALOG = [
  {
    id: "01",
    path: "/labs/01",
    title: "Browser ready",
    blurb: "Confirm secure context and Web Bluetooth support.",
  },
  {
    id: "02",
    path: "/labs/02",
    title: "Pick the board",
    blurb: "User-gesture requestDevice for TESAIoT-*.",
  },
  {
    id: "03",
    path: "/labs/03",
    title: "Open the GATT link",
    blurb: "Connect GATT, discover BS2 chars, read BS_LINK.",
  },
  {
    id: "04",
    path: "/labs/04",
    title: "Hear the first events",
    blurb: "Enable BS_TX notifications and decode EVT_SENSOR.",
  },
  {
    id: "05",
    path: "/labs/05",
    title: "Prove the stream",
    blurb: "Hybrid publish for all six sensors — live counters.",
  },
  {
    id: "06",
    path: "/labs/06",
    title: "Steer one sensor",
    blurb: "Fire-and-forget SENSOR_CFG_SET to focus traffic.",
  },
  {
    id: "07",
    path: "/labs/07",
    title: "Motion + climate",
    blurb: "BMI270, magnetometer, and environment cards.",
  },
  {
    id: "08",
    path: "/labs/08",
    title: "Knobs and buttons",
    blurb: "ADC_POT and SW_BTN on-board HMI.",
  },
  {
    id: "09",
    path: "/labs/09",
    title: "Live board",
    blurb: "Compose six cards, link status, and a session log.",
  },
  {
    id: "10",
    path: "/labs/10",
    title: "Your scaffold",
    blurb: "Choose a sensor set — then graduate to the dashboard app.",
  },
] as const;

export function labPath(id: string): string {
  return `/labs/${id}`;
}

export function adjacentLabs(id: string): { prevPath?: string; nextPath?: string } {
  const idx = LAB_CATALOG.findIndex((l) => l.id === id);
  if (idx < 0) return {};
  return {
    prevPath: idx > 0 ? LAB_CATALOG[idx - 1].path : undefined,
    nextPath: idx < LAB_CATALOG.length - 1 ? LAB_CATALOG[idx + 1].path : undefined,
  };
}
