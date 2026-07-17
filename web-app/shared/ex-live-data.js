/**
 * LiveDataClient loader for hackathon SDK MQTT / WebSocket examples (ex13, ex15).
 * Tries VSIX serve path first, then bundled vendor fallback (same bundle as ex-demo).
 */

const SDK_IMPORT_CANDIDATES = [
  '/@bitstream/ws-live-data.js',
  '/sdk/live-data.js',
  new URL('../vendor/live-data.js', import.meta.url).href,
];

export async function loadLiveDataClient() {
  let lastErr;
  for (const url of SDK_IMPORT_CANDIDATES) {
    try {
      const mod = await import(/* @vite-ignore */ url);
      if (mod.LiveDataClient) {
        return {
          LiveDataClient: mod.LiveDataClient,
          DEFAULT_MQTT_WS_URL: mod.DEFAULT_MQTT_WS_URL,
          DEFAULT_T3D_WS_URL: mod.DEFAULT_T3D_WS_URL,
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
