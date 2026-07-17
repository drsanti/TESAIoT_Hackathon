#!/usr/bin/env node
/**
 * Static smoke checks for TESAIoT_Hackathon/web-app examples.
 * Run with smoke-serve.mjs on port 8899 for HTTP checks.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const BASE = process.env.SMOKE_BASE_URL || 'http://127.0.0.1:8899';

const EXAMPLES = [
  'index.html',
  'ex01_sht40.html',
  'ex02_dps368.html',
  'ex03_bmm350.html',
  'ex04_bmi270_imu.html',
  'ex05_bmi270_orientation.html',
  'ex06_dashboard.html',
  'ex07_catalog_browser.html',
  'ex08_stale_and_route.html',
  'ex09_mqtt_subscriber.html',
  'ex10_mqtt_publisher.html',
  'ex11_mqtt_wildcards.html',
  'ex12_mqtt_devkit_gauges.html',
  'ex13_mqtt_live_data_client.html',
  'ex14_mqtt_qos_retain.html',
  'ex15_ws_mqtt_dashboard.html',
];

const SDK_PATHS = ['/@bitstream/ws-live-data.js', '/@bitstream/mqtt-live-data.js'];

function localRefs(html, file) {
  const broken = [];
  const dir = path.dirname(file);
  for (const m of html.matchAll(/(?:href|src)=["']([^"']+)["']/g)) {
    const ref = m[1];
    if (ref.startsWith('http') || ref.startsWith('#') || ref.startsWith('?')) continue;
    const p = path.normalize(path.join(dir, ref));
    if (!fs.existsSync(p)) broken.push(ref);
  }
  for (const m of html.matchAll(/from ["']([^"']+)["']/g)) {
    const ref = m[1];
    if (ref.startsWith('http')) continue;
    const p = path.normalize(path.join(dir, ref));
    if (!fs.existsSync(p)) broken.push(ref);
  }
  return broken;
}

async function httpOk(url) {
  const res = await fetch(url, { redirect: 'follow' });
  return { url, status: res.status, ok: res.ok };
}

async function main() {
  let failed = 0;

  // Vendor SDK import (offline path for ex01–ex08, ex13, ex15)
  try {
    const mod = await import(
      pathToFileURL(path.join(WEB_ROOT, 'vendor/live-data.js')).href
    );
    const required = ['TelemetryClient', 'LiveDataClient', 'catalogEntry', 'SENSOR_CATALOG'];
    for (const k of required) {
      if (typeof mod[k] === 'undefined') {
        console.error(`[FAIL] vendor missing export: ${k}`);
        failed += 1;
      }
    }
    const ids = mod.SENSOR_CATALOG.sensors.map((s) => s.id).sort().join(',');
    if (ids !== 'bmi270,bmm350,dps368,sht40') {
      console.error(`[FAIL] unexpected catalog sensors: ${ids}`);
      failed += 1;
    } else {
      console.log('[OK] vendor/live-data.js exports + catalog');
    }
  } catch (e) {
    console.error('[FAIL] vendor import:', e.message);
    failed += 1;
  }

  // Local file refs
  for (const name of EXAMPLES) {
    const file = path.join(WEB_ROOT, name);
    const html = fs.readFileSync(file, 'utf8');
    const broken = localRefs(html, file);
    if (broken.length) {
      console.error(`[FAIL] ${name} broken refs:`, broken.join(', '));
      failed += 1;
    } else {
      console.log(`[OK] ${name} local refs`);
    }
  }

  // HTTP (optional — server must be running)
  let httpFailed = false;
  for (const name of EXAMPLES) {
    const r = await httpOk(`${BASE}/${name}`);
    if (!r.ok) {
      console.error(`[FAIL] HTTP ${r.status} ${r.url}`);
      httpFailed = true;
      failed += 1;
    }
  }
  for (const p of SDK_PATHS) {
    const r = await httpOk(`${BASE}${p}`);
    if (!r.ok) {
      console.error(`[FAIL] HTTP ${r.status} ${r.url}`);
      httpFailed = true;
      failed += 1;
    }
  }
  if (!httpFailed) {
    console.log(`[OK] HTTP ${BASE} — all pages + SDK paths`);
  }

  process.exit(failed > 0 ? 1 : 0);
}

function pathToFileURL(p) {
  const u = path.resolve(p).replace(/\\/g, '/');
  return new URL(`file:///${u.startsWith('/') ? u.slice(1) : u}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
