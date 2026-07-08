/**
 * Shared helpers for Bitstream Studio TESAIoT_Hackathon examples (ex02–ex08).
 * ex01 remains self-contained; import this module from sibling HTML pages.
 */

/** Import URLs tried in order (VSIX serve → legacy alias → bundled vendor copy). */
const SDK_IMPORT_CANDIDATES = [
  '/@bitstream/ws-live-data.js',
  '/sdk/live-data.js',
  new URL('../vendor/live-data.js', import.meta.url).href,
];

/** Load TelemetryClient + catalog from VSIX SDK or local vendor fallback. */
export async function loadSdk() {
  let lastErr;
  for (const url of SDK_IMPORT_CANDIDATES) {
    try {
      const mod = await import(/* @vite-ignore */ url);
      if (mod.TelemetryClient) {
        return {
          TelemetryClient: mod.TelemetryClient,
          catalogEntry: mod.catalogEntry,
          SENSOR_CATALOG: mod.SENSOR_CATALOG,
        };
      }
    } catch (err) {
      lastErr = err;
    }
  }
  const hint =
    'Live-data SDK not found. Use Bitstream Studio → "Serve Web App Folder over HTTP", or copy packages/live-data/dist/live-data.browser.js to web-app/vendor/live-data.js.';
  const err = new Error(hint);
  err.cause = lastErr;
  throw err;
}

/** Map a value to 0–100% using catalog field min/max. */
export function pct(v, def) {
  if (!def || def.max === def.min) return 0;
  return Math.max(0, Math.min(100, ((v - def.min) / (def.max - def.min)) * 100));
}

/** Compact per-sample meta line (counter, origin, device time). */
export function formatMeta(sample) {
  return `#${sample.counter} · ${sample.origin ?? '?'} · device ${sample.deviceMs} ms`;
}

/**
 * Client-side stale timer (mirrors catalog staleAfterMs).
 * Returns { touch, dispose } — call touch() on each fresh sample.
 */
export function createStaleTracker(staleAfterMs, onStale) {
  let timer = null;
  return {
    touch() {
      onStale(false);
      clearTimeout(timer);
      timer = setTimeout(() => onStale(true), staleAfterMs);
    },
    dispose() {
      clearTimeout(timer);
    },
  };
}

/** Wire connection badge + route label (matches ex01). */
export function wireConnectionBadge(client, stateEl, routeEl) {
  client.on('connection', (c) => {
    stateEl.textContent = c.state;
    stateEl.className = c.state;
    routeEl.textContent = c.state === 'connected' ? `route: ${c.route}` : '';
  });
}

/** Connect with friendly failure message on route element. */
export async function connectTelemetry(
  client,
  routeEl,
  failMsg = 'provider not reachable — start Bitstream Studio services',
) {
  try {
    await client.connect();
  } catch {
    routeEl.textContent = failMsg;
  }
}

/** Draw one normalized series on a canvas 2D context. */
export function drawSeries(ctx, series, color, min, max, width, height, pad = 8) {
  if (series.length < 2) return;
  const span = max - min || 1;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  series.forEach((v, i) => {
    const x = (i / (series.length - 1)) * width;
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

/** Auto-scaled sparkline / chart for a single series. */
export function drawSparkline(ctx, canvas, series, color, maxPoints = 120) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (series.length < 2) return;
  const min = Math.min(...series);
  const max = Math.max(...series);
  drawSeries(ctx, series, color, min, max, canvas.width, canvas.height);
}

/** Push into a fixed-length history buffer. */
export function pushHistory(buf, value, max = 120) {
  buf.push(value);
  if (buf.length > max) buf.shift();
}

/** Find a catalog field definition by key. */
export function fieldDef(entry, key) {
  return entry?.fields?.find((f) => f.key === key);
}

/** BMI270 quaternion → Euler radians (heading, pitch, roll). */
export function quatToEuler(w, x, y, z) {
  const sinr = 2 * (w * x + y * z);
  const cosr = 1 - 2 * (x * x + y * y);
  const roll = Math.atan2(sinr, cosr);
  const sinp = 2 * (w * y - z * x);
  const pitch = Math.abs(sinp) >= 1 ? Math.sign(sinp) * (Math.PI / 2) : Math.asin(sinp);
  const siny = 2 * (w * z + x * y);
  const cosy = 1 - 2 * (y * y + z * z);
  const heading = Math.atan2(siny, cosy);
  return { headingRad: heading, pitchRad: pitch, rollRad: roll };
}

/** Resolve orientation from BMI270 sample (Euler preferred, quaternion fallback). */
export function resolveOrientation(fields) {
  if (
    typeof fields.headingRad === 'number' &&
    typeof fields.pitchRad === 'number' &&
    typeof fields.rollRad === 'number'
  ) {
    return {
      headingRad: fields.headingRad,
      pitchRad: fields.pitchRad,
      rollRad: fields.rollRad,
      source: 'euler',
    };
  }
  if (
    typeof fields.quatW === 'number' &&
    typeof fields.quatX === 'number' &&
    typeof fields.quatY === 'number' &&
    typeof fields.quatZ === 'number'
  ) {
    const e = quatToEuler(fields.quatW, fields.quatX, fields.quatY, fields.quatZ);
    return { ...e, source: 'quaternion' };
  }
  return null;
}

/** Draw artificial horizon (pitch + roll) on canvas. */
export function drawHorizon(ctx, canvas, pitchRad, rollRad) {
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  ctx.clearRect(0, 0, w, h);

  // Sky / ground
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(-rollRad);
  const pitchPx = (pitchRad / (Math.PI / 2)) * (h * 0.45);
  ctx.fillStyle = '#6eb5ff';
  ctx.fillRect(-w, -h + pitchPx, w * 2, h);
  ctx.fillStyle = '#8b6914';
  ctx.fillRect(-w, pitchPx, w * 2, h);
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(-w, pitchPx);
  ctx.lineTo(w, pitchPx);
  ctx.stroke();
  ctx.restore();

  // Fixed aircraft symbol
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(cx - 50, cy);
  ctx.lineTo(cx - 12, cy);
  ctx.moveTo(cx + 50, cy);
  ctx.lineTo(cx + 12, cy);
  ctx.moveTo(cx, cy - 8);
  ctx.lineTo(cx, cy + 8);
  ctx.stroke();

  // Bezel
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(cx, cy, Math.min(w, h) * 0.42, 0, Math.PI * 2);
  ctx.stroke();
}

/** Draw 2D compass needle from heading radians. */
export function drawCompass(ctx, canvas, headingRad) {
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(w, h) * 0.42;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = '#ccc';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();

  ctx.fillStyle = '#333';
  ctx.font = 'bold 12px system-ui';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('N', cx, cy - r + 14);

  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(headingRad);
  ctx.fillStyle = '#e0563a';
  ctx.beginPath();
  ctx.moveTo(0, -r + 18);
  ctx.lineTo(-8, 10);
  ctx.lineTo(8, 10);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#888';
  ctx.beginPath();
  ctx.moveTo(0, r - 18);
  ctx.lineTo(-8, -10);
  ctx.lineTo(8, -10);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
