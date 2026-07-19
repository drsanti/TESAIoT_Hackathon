"""Diagnostic log helpers for pasting into chat / bug reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def format_log_line(level: str, text: str, *, stamp: str | None = None) -> str:
    ts = stamp or utc_stamp()
    tag = (level or "info").upper()[:5]
    safe = (
        text.replace("\u2026", "...")
        .replace("\u2014", "-")
        .replace("\u00b7", "|")
    )
    return f"[{ts}] {tag:<5} {safe}"


def build_session_snapshot(
    *,
    phase: str,
    auto_enabled: bool,
    last_address: str | None,
    last_device_name: str | None = None,
    last_preset_id: str,
    hunt_fails: int,
    state: Any,
    frame_stats_lines: dict[str, str],
    count_window_s: float,
    note: str = "",
) -> str:
    """Plain-text dump for copy/paste analysis."""
    lines: list[str] = [
        "=== TESAIoT BLE Flet - session snapshot ===",
        f"utc={datetime.now(timezone.utc).isoformat()}",
        f"phase={phase}  auto={auto_enabled}  hunt_fails={hunt_fails}",
        f"last_address={last_address or '-'}  last_name={last_device_name or '-'}  last_preset={last_preset_id}",
        f"count_window_s={count_window_s:.1f}",
    ]
    if note:
        lines.append(f"note={note}")

    connected = bool(getattr(state, "connected", False))
    lines.append(
        f"connected={connected}  name={getattr(state, 'device_name', '') or '-'}  "
        f"addr={getattr(state, 'device_address', '') or '-'}"
    )
    pol = int(getattr(state, "policy_flags", 0) or 0)
    lines.append(
        f"policy=0x{pol:02x}  streaming={bool(getattr(state, 'streaming', False))}  "
        f"tx_evt={bool(pol & 0x02)}  adv={bool(pol & 0x01)}  rx_req={bool(pol & 0x04)}"
    )
    lines.append(
        f"BS_LINK state={getattr(state, 'link_state', 0)}  "
        f"mtu={getattr(state, 'link_mtu', 0)}  tx_drops={getattr(state, 'link_tx_drops', 0)}  "
        f"peak_device_ms={getattr(state, 'peak_device_ms', 0)}"
    )

    cfg = getattr(state, "sensor_cfg", {}) or {}
    unique = getattr(state, "frame_unique", {}) or {}
    raw = getattr(state, "frame_raw", {}) or {}
    lines.append("--- sensors ---")
    for key in ("bmi270", "bmm350", "sht40", "dps368"):
        row = cfg.get(key)
        cfg_bits = "-"
        if isinstance(row, dict):
            cfg_bits = (
                f"en={int(bool(row.get('enabled')))} mask=0x{int(row.get('mask', 0)):02x} "
                f"mode={row.get('publish_mode', '-')} int_ms={row.get('interval_ms', '-')}"
            )
        stats = frame_stats_lines.get(key, "-")
        lines.append(
            f"{key}: evt={unique.get(key, 0)} raw={raw.get(key, 0)}  cfg[{cfg_bits}]  {stats}"
        )

    lines.append("=== end snapshot ===")
    text = "\n".join(lines)
    return text.replace("\u2026", "...").replace("\u2014", "-").replace("\u00b7", "|")
