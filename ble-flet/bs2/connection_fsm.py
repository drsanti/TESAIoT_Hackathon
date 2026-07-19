"""UX connection state machine for the Flet BLE dashboard."""

from __future__ import annotations

from enum import Enum


class ConnPhase(str, Enum):
    IDLE = "idle"
    PARKED = "parked"
    HUNTING = "hunting"
    CONNECTING = "connecting"
    LINKED = "linked"
    LIVE = "live"
    RECOVERING = "recovering"


# Hunt backoff seconds (index = consecutive empty / failed attempts). Cap at last.
HUNT_BACKOFF_S = (2.0, 4.0, 8.0, 8.0)
RECOVER_GRACE_S = 1.5
# Manual scene presets (Connect / Live page) — not applied on Auto connect.
DEFAULT_SCENE_PRESET = "motion"
# Auto connect uses firmware boot SENSOR_CFG (viewer); no scene push.
VIEWER_PRESET_LABEL = "device"


def phase_chip_label(
    phase: ConnPhase,
    *,
    device_name: str = "",
    preset_id: str | None = None,
    streaming: bool = False,
) -> str:
    if phase is ConnPhase.IDLE:
        return "Disconnected"
    if phase is ConnPhase.PARKED:
        return "Paused (manual)"
    if phase is ConnPhase.HUNTING:
        return "Looking for board..."
    if phase is ConnPhase.CONNECTING:
        return f"Connecting{f' · {device_name}' if device_name else ''}..."
    if phase is ConnPhase.LINKED:
        return f"Connected · quiet{f' · {device_name}' if device_name else ''}"
    if phase is ConnPhase.LIVE:
        preset = preset_id or VIEWER_PRESET_LABEL
        if streaming:
            return f"Streaming · {preset}"
        return f"Connected · {preset}"
    if phase is ConnPhase.RECOVERING:
        return "Link lost · reconnecting..."
    return phase.value


def phase_chip_color(phase: ConnPhase) -> str:
    if phase is ConnPhase.LIVE:
        return "green"
    if phase in (ConnPhase.HUNTING, ConnPhase.CONNECTING, ConnPhase.RECOVERING, ConnPhase.LINKED):
        return "amber"
    if phase is ConnPhase.PARKED:
        return "grey"
    return "grey"
