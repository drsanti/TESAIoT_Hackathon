/**
 * LiveDataClient loader for hackathon SDK MQTT / WebSocket examples.
 */

export async function loadLiveDataClient() {
  const mod = await import("/@bitstream/ws-live-data.js");
  return {
    LiveDataClient: mod.LiveDataClient,
    DEFAULT_MQTT_WS_URL: mod.DEFAULT_MQTT_WS_URL,
    DEFAULT_T3D_WS_URL: mod.DEFAULT_T3D_WS_URL,
  };
}
