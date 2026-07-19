/**
 * Fresh Node Web Bluetooth step diagnostic (thegecko/webbluetooth).
 *
 * Same step shape as http://localhost:5174/diag and python-app/tools/ble_step_diag.py.
 * Runs in Node — does NOT fix Chrome. Use to compare host stacks:
 *   bleak (Python) vs webbluetooth (Node) vs Chrome navigator.bluetooth.
 *
 *   cd ble-react/tools/webbluetooth-diag
 *   npm install
 *   npm run diag
 *
 * Close Chrome /diag and Python labs first (one central).
 */
import { Bluetooth } from "webbluetooth";

const SERVICE = "6f6b7a80-0001-4000-8000-00805f9b34fb";
const BS_RX = "6f6b7a80-0001-4001-8000-00805f9b34fb";
const BS_TX = "6f6b7a80-0001-4002-8000-00805f9b34fb";
const BS_LINK = "6f6b7a80-0001-4003-8000-00805f9b34fb";
const NAME_PREFIX = "TESAIoT-";

const SCAN_MS = 12_000;

function msNow() {
  return performance.now();
}

function log(mark, name, detail = "", elapsedMs = 0) {
  const timing = elapsedMs ? ` (${elapsedMs.toFixed(0)} ms)` : "";
  console.log(`[${mark}] ${name}${timing}`);
  if (detail) {
    for (const line of String(detail).split("\n")) {
      console.log(`       ${line}`);
    }
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  console.log("=".repeat(60));
  console.log("Fresh BLE step diagnostic (Node webbluetooth / SimpleBLE)");
  console.log("API-shaped like browser navigator.bluetooth — NOT Chrome itself");
  console.log("=".repeat(60));
  console.log();

  const results = [];
  let device = null;
  let server = null;

  const bluetooth = new Bluetooth({
    scanTime: SCAN_MS,
    deviceFound: (dev, _selectFn) => {
      const name = dev.name || "";
      if (name.startsWith(NAME_PREFIX)) {
        console.log(`       seen ${name} id=${dev.id}`);
        return true; // auto-select first TESAIoT-*
      }
      return false;
    },
  });

  try {
    // 1 — API present
    let t0 = msNow();
    if (typeof bluetooth.requestDevice !== "function") {
      log("FAIL", "1 API", "bluetooth.requestDevice missing");
      results.push(false);
      return exitSummary(results);
    }
    log("PASS", "1 API", "webbluetooth Bluetooth.requestDevice available", msNow() - t0);
    results.push(true);

    // 2 — requestDevice (scan + pick)
    t0 = msNow();
    try {
      device = await bluetooth.requestDevice({
        filters: [{ namePrefix: NAME_PREFIX }],
        optionalServices: [SERVICE],
      });
      log(
        "PASS",
        "2 requestDevice",
        `${device.name || "(unnamed)"} id=${device.id}`,
        msNow() - t0,
      );
      results.push(true);
    } catch (e) {
      log("FAIL", "2 requestDevice", errText(e), msNow() - t0);
      results.push(false);
      return exitSummary(results);
    }

    // 3 — gatt.connect
    t0 = msNow();
    try {
      if (!device.gatt) throw new Error("device.gatt is null");
      server = await device.gatt.connect();
      log("PASS", "3 gatt.connect", `connected=${server.connected}`, msNow() - t0);
      results.push(true);
    } catch (e) {
      log("FAIL", "3 gatt.connect", errText(e), msNow() - t0);
      results.push(false);
      return exitSummary(results);
    }

    await sleep(800);

    // 4 — getPrimaryService
    t0 = msNow();
    let service;
    try {
      // Full enum first (helps some SimpleBLE builds populate char tables).
      try {
        await server.getPrimaryServices();
      } catch {
        /* optional */
      }
      service = await server.getPrimaryService(SERVICE);
      log("PASS", "4 getPrimaryService", String(service.uuid), msNow() - t0);
      results.push(true);
    } catch (e) {
      log("FAIL", "4 getPrimaryService", errText(e), msNow() - t0);
      results.push(false);
      return exitSummary(results);
    }

    // 5 — characteristics (retry: SimpleBLE on Win sometimes returns empty first)
    t0 = msNow();
    let rx;
    let tx;
    let link;
    try {
      let all = [];
      for (let attempt = 1; attempt <= 4; attempt++) {
        // Force re-discover by clearing cached list if the lib exposes it.
        service.characteristics = undefined;
        all = await service.getCharacteristics();
        if (all.length > 0) break;
        await sleep(500 * attempt);
      }

      const find = (want) => all.find((c) => uuidEq(String(c.uuid), want)) ?? null;
      rx = find(BS_RX);
      tx = find(BS_TX);
      link = find(BS_LINK);

      if (!rx || !tx || !link) {
        try {
          rx = rx ?? (await service.getCharacteristic(BS_RX));
          tx = tx ?? (await service.getCharacteristic(BS_TX));
          link = link ?? (await service.getCharacteristic(BS_LINK));
        } catch {
          /* keep nulls */
        }
      }

      if (!rx || !tx || !link) {
        const listed = all
          .map((c) => `  ${c.uuid}  props=${JSON.stringify(c.properties)}`)
          .join("\n");
        throw new Error(
          `missing BS_RX/TX/LINK. service has ${all.length} char(s):\n${listed || "  (none)"}\n` +
            "Note: thegecko/webbluetooth (SimpleBLE) on Windows often sees the BS2 service " +
            "but 0 characteristics. Use python-app/tools/ble_step_diag.py for host char/LINK checks.",
        );
      }

      log(
        "PASS",
        "5 getCharacteristic",
        `RX/TX/LINK ok  TX.notify=${Boolean(tx.properties?.notify)}`,
        msNow() - t0,
      );
      results.push(true);
    } catch (e) {
      log("FAIL", "5 getCharacteristic", errText(e), msNow() - t0);
      results.push(false);
      return exitSummary(results);
    }

    // 6 — read BS_LINK
    t0 = msNow();
    try {
      const value = await link.readValue();
      const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
      const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
      log(
        "PASS",
        "6 read BS_LINK",
        `len=${bytes.length} hex=${hex} state=${bytes[0] ?? "?"}`,
        msNow() - t0,
      );
      results.push(true);
    } catch (e) {
      log("FAIL", "6 read BS_LINK", errText(e), msNow() - t0);
      results.push(false);
      return exitSummary(results);
    }

    // 7 — startNotifications (optional stream)
    t0 = msNow();
    try {
      let n = 0;
      const onChange = () => {
        n += 1;
      };
      tx.addEventListener("characteristicvaluechanged", onChange);
      await tx.startNotifications();
      await sleep(2500);
      await tx.stopNotifications();
      tx.removeEventListener("characteristicvaluechanged", onChange);
      log(
        "PASS",
        "7 startNotifications",
        `CCCD on; ${n} notify(s) in 2.5s (0 OK without SENSOR_CFG stream)`,
        msNow() - t0,
      );
      results.push(true);
    } catch (e) {
      log("FAIL", "7 startNotifications", errText(e), msNow() - t0);
      results.push(false);
    }

    return exitSummary(results);
  } finally {
    try {
      if (server?.connected) server.disconnect();
      else if (device?.gatt?.connected) device.gatt.disconnect();
      console.log("\nDisconnected (cleanup).");
    } catch (e) {
      console.log(`\nDisconnect warning: ${errText(e)}`);
    }
  }
}

function errText(e) {
  if (e instanceof Error) return `${e.name}: ${e.message}`;
  return String(e);
}

function uuidEq(a, b) {
  return a.replace(/-/g, "").toLowerCase() === b.replace(/-/g, "").toLowerCase();
}

function exitSummary(results) {
  console.log();
  console.log("-".repeat(60));
  console.log("SUMMARY");
  const labels = [
    "1 API",
    "2 requestDevice",
    "3 gatt.connect",
    "4 getPrimaryService",
    "5 getCharacteristic",
    "6 read BS_LINK",
    "7 startNotifications",
  ];
  for (let i = 0; i < results.length; i++) {
    console.log(`  ${results[i] ? "PASS" : "FAIL"}  ${labels[i] ?? `step ${i + 1}`}`);
  }
  const failed = results.filter((x) => !x).length;
  console.log();
  if (failed === 0) {
    console.log("Node webbluetooth path OK (host SimpleBLE).");
    console.log("If Chrome /diag still fails at step 3, that is browser WinRT — not firmware.");
  } else {
    console.log(`${failed} step(s) failed - RESET board to soft-blue; one central only.`);
  }
  return failed === 0 ? 0 : 1;
}

const code = await main();
process.exit(code);
