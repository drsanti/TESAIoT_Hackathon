"""User preferences — ~/.tesaiot/ble-flet-prefs.json"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SENSOR_KEYS = ("bmi270", "bmm350", "sht40", "dps368")
ROUTES = ("live", "connect", "log", "settings")
LAYOUT_PRESETS = ("grid", "stack", "focus")
PLOT_MODES = ("bars", "lines")

_DEFAULT_PLOT_MODE = {k: "bars" for k in SENSOR_KEYS}


def prefs_path() -> Path:
    home = Path.home()
    return home / ".tesaiot" / "ble-flet-prefs.json"


@dataclass
class AppPreferences:
    sidebar_collapsed: bool = False
    active_route: str = "live"
    layout_preset: str = "grid"
    focus_sensor: str = "bmi270"
    plot_mode: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_PLOT_MODE))
    update_on_data: bool = False
    auto_enabled: bool = True

    def normalize(self) -> None:
        if self.active_route not in ROUTES:
            self.active_route = "live"
        if self.layout_preset not in LAYOUT_PRESETS:
            self.layout_preset = "grid"
        if self.focus_sensor not in SENSOR_KEYS:
            self.focus_sensor = "bmi270"
        for key in SENSOR_KEYS:
            mode = self.plot_mode.get(key, "bars")
            if mode not in PLOT_MODES:
                self.plot_mode[key] = "bars"


class PreferencesStore:
    def __init__(self) -> None:
        self.prefs = AppPreferences()
        self._save_task: asyncio.Task | None = None
        self._dirty = False

    def load(self) -> AppPreferences:
        path = prefs_path()
        if not path.is_file():
            self.prefs.normalize()
            return self.prefs
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            self.prefs = AppPreferences(
                sidebar_collapsed=bool(raw.get("sidebar_collapsed", False)),
                active_route=str(raw.get("active_route", "live")),
                layout_preset=str(raw.get("layout_preset", "grid")),
                focus_sensor=str(raw.get("focus_sensor", "bmi270")),
                plot_mode=dict(raw.get("plot_mode") or _DEFAULT_PLOT_MODE),
                update_on_data=bool(raw.get("update_on_data", False)),
                auto_enabled=bool(raw.get("auto_enabled", True)),
            )
        except (OSError, json.JSONDecodeError, TypeError):
            self.prefs = AppPreferences()
        self.prefs.normalize()
        return self.prefs

    def _write(self) -> None:
        path = prefs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self.prefs), indent=2) + "\n",
            encoding="utf-8",
        )
        self._dirty = False

    def save_now(self) -> None:
        self.prefs.normalize()
        self._write()

    def schedule_save(self) -> None:
        self._dirty = True
        task = self._save_task
        if task is not None and not task.done():
            return

        async def _delayed() -> None:
            try:
                await asyncio.sleep(0.3)
                if self._dirty:
                    self._write()
            except asyncio.CancelledError:
                return

        try:
            self._save_task = asyncio.get_running_loop().create_task(_delayed())
        except RuntimeError:
            self._write()
