/**
 * Shared MQTT helpers for hackathon Connectivity examples (ex09+).
 * Loads raw mqtt.js from /@bitstream/mqtt-live-data.js (Serve Web App Folder).
 */

export const DEFAULT_MQTT_WS_PATH = "ws://127.0.0.1:8883/mqtt";

export async function loadMqttGlobal() {
  if (typeof globalThis.mqtt !== "undefined") {
    return globalThis.mqtt;
  }
  await new Promise((resolve, reject) => {
    const el = document.createElement("script");
    el.src = "/@bitstream/mqtt-live-data.js";
    el.async = true;
    el.onload = resolve;
    el.onerror = () => reject(new Error("/@bitstream/mqtt-live-data.js"));
    document.head.appendChild(el);
  });
  if (typeof globalThis.mqtt === "undefined") {
    throw new Error("mqtt global missing after /@bitstream/mqtt-live-data.js");
  }
  return globalThis.mqtt;
}

export function queryParam(key, fallback) {
  try {
    const value = new URLSearchParams(window.location.search).get(key);
    if (value != null && value.trim().length > 0) {
      return value.trim();
    }
  } catch {
    /* ignore */
  }
  return fallback;
}

export function devkitTwinTopic(deviceId) {
  return `device/${deviceId}/devkit-twin/telemetry`;
}

export function connectMqtt(mqtt, url, extra = {}) {
  return mqtt.connect(url, {
    reconnectPeriod: 2000,
    connectTimeout: 8000,
    ...extra,
  });
}

/** Wire #state badge for raw mqtt.js clients. */
export function wireMqttState(client, stateEl, handlers = {}) {
  client.on("connect", () => {
    stateEl.textContent = "connected";
    stateEl.className = "connected";
    handlers.onConnect?.();
  });
  client.on("reconnect", () => {
    stateEl.textContent = "reconnecting";
    stateEl.className = "";
    handlers.onReconnect?.();
  });
  client.on("error", (err) => {
    stateEl.textContent = "error";
    stateEl.className = "";
    handlers.onError?.(err);
  });
  client.on("close", () => {
    stateEl.textContent = "disconnected";
    stateEl.className = "";
    handlers.onClose?.();
  });
}

export function setChip(id, text, tone) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "chip" + (tone ? " " + tone : "");
  const span = el.querySelector("span");
  if (span) span.textContent = text;
}

export function appendLog(logEl, line, maxLines = 50) {
  const lines = logEl.textContent ? logEl.textContent.split("\n") : [];
  lines.unshift(line);
  while (lines.length > maxLines) lines.pop();
  logEl.textContent = lines.join("\n");
}
