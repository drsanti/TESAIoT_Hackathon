"""Flet UI for TESAIoT BLE BS2 dashboard — sidebar shell + Auto hunt."""

from __future__ import annotations

import asyncio
import time

import flet as ft
from bleak.backends.device import BLEDevice

from bs2 import Bs2BleSession, SessionState
from bs2.connection_fsm import (
    AUTO_STREAM_SCENE_PRESET,
    DEFAULT_SCENE_PRESET,
    HUNT_BACKOFF_S,
    RECOVER_GRACE_S,
    ConnPhase,
    phase_chip_color,
    phase_chip_label,
)
from bs2.decode import SENSOR_LABELS
from bs2.gatt import device_identity_key
from ui.app_shell import AppShell, build_top_bar
from ui.diag_log import build_session_snapshot, format_log_line
from ui.live_grid import LiveGridHost
from ui.live_widgets import SensorLiveCard
from ui.pages.connect_page import ConnectPage
from ui.pages.live_page import LivePage
from ui.pages.log_page import LogPage
from ui.pages.settings_page import SettingsPage
from ui.preferences import PreferencesStore
from ui.sidebar import SidebarNav
from ui.status_hero import StatusHero
from ui.theme import ROUTE_LABELS, TEXT_MUTED

_UI_PAINT_INTERVAL_S = 0.25
_LOG_MAX_LINES = 400
_BLE_POLICY_STREAMING = 0x07


def _fmt_fields(fields: dict[str, float]) -> str:
    if not fields:
        return "-"
    parts: list[str] = []
    for key, value in fields.items():
        parts.append(f"{key}={value:.2f}")
    return " · ".join(parts[:6])


class BleDashboardApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.prefs_store = PreferencesStore()
        self.prefs = self.prefs_store.load()

        self.devices: list[BLEDevice] = []
        self.session = Bs2BleSession(
            on_log=self._on_log,
            on_sample=self._on_sample,
            on_state=self._on_state,
            on_link_lost=self._on_link_lost,
        )

        self.phase = ConnPhase.IDLE
        self.auto_enabled = self.prefs.auto_enabled
        self.update_on_data = self.prefs.update_on_data
        self.last_address: str | None = None
        self.last_device_name: str | None = None
        self.last_preset_id = DEFAULT_SCENE_PRESET
        self._hunt_fails = 0
        self._auto_task: asyncio.Task | None = None
        self._auto_gen = 0

        self.device_dropdown = ft.Dropdown(
            label="Peripheral",
            width=320,
            options=[],
            disabled=True,
        )
        self._connect_btn = ft.ElevatedButton(
            "Connect",
            icon=ft.Icons.LINK,
            on_click=lambda e: self._run_task(self._connect(e)),
        )
        self.policy_text = ft.Text("policy —", size=12, color=ft.Colors.GREY_500)
        self.link_text = ft.Text("BS_LINK —", size=12, color=ft.Colors.GREY_500)
        self.status_text = ft.Text("Disconnected", color=ft.Colors.GREY_400)
        self.window_text = ft.Text("count window —", size=12, color=TEXT_MUTED)
        self.live_hint = ft.Text(
            "Auto will find the board and open Live when streaming.",
            size=12,
            color=TEXT_MUTED,
        )

        self.log_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self._log_lines: list[str] = []
        self.log_meta = ft.Text("0 lines", size=11, color=ft.Colors.GREY_500)
        self.log_copy_status = ft.Text("", size=11, color=ft.Colors.GREEN_300)

        self.auto_switch = ft.Switch(
            label="Auto",
            value=self.auto_enabled,
            on_change=self._on_auto_toggle,
        )
        self.update_on_data_switch = ft.Switch(
            label="Update on data",
            value=self.update_on_data,
            on_change=self._on_update_on_data_toggle,
        )

        self.sensor_tiles: dict[str, ft.Card] = {}
        self.sensor_meta: dict[str, ft.Text] = {}
        self.sensor_stats: dict[str, ft.Text] = {}
        self.sensor_values: dict[str, ft.Text] = {}
        self.live_cards: dict[str, SensorLiveCard] = {}

        self._pending_samples: dict[str, dict] = {}
        self._last_ui_paint_s = 0.0
        self._ui_flush_task: asyncio.Task | None = None
        self._chrome_dirty = False

        for key in ("bmi270", "bmm350", "sht40", "dps368"):
            meta = ft.Text("waiting…", size=11, color=ft.Colors.GREY_500)
            stats = ft.Text(
                "frames evt=0  raw=0  cfg —  meas —  […]",
                size=11,
                color=ft.Colors.CYAN_200,
            )
            values = ft.Text("—", size=13)
            self.sensor_meta[key] = meta
            self.sensor_stats[key] = stats
            self.sensor_values[key] = values
            self.sensor_tiles[key] = ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        [
                            ft.Text(SENSOR_LABELS[key], weight=ft.FontWeight.W_600, size=14),
                            meta,
                            stats,
                            values,
                        ],
                        spacing=6,
                    ),
                ),
            )
            plot_mode = self.prefs.plot_mode.get(key, "bars")
            self.live_cards[key] = SensorLiveCard(
                key,
                plot_mode=plot_mode,
                on_plot_mode_change=self._on_card_plot_mode,
            )

        self.hero = StatusHero(on_stream_on=lambda e: self._run_task(self._stream_on(e)))
        self.grid_host = LiveGridHost()
        self._scene_row = self._build_scene_row()

        self.live_page = LivePage(
            hero=self.hero,
            grid_host=self.grid_host,
            layout_preset=self.prefs.layout_preset,
            focus_sensor=self.prefs.focus_sensor,
            on_layout=self._set_layout_preset,
            on_focus_sensor=self._set_focus_sensor,
            scene_row=self._scene_row,
            footer_row=ft.Row(
                [self.window_text, self.update_on_data_switch],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            hint=self.live_hint,
        )

        self.connect_page = ConnectPage(
            device_dropdown=self.device_dropdown,
            scan_btn=ft.ElevatedButton(
                "Scan",
                icon=ft.Icons.BLUETOOTH_SEARCHING,
                on_click=lambda e: self._run_task(self._scan(e)),
            ),
            connect_btn=self._connect_btn,
            park_btn=ft.OutlinedButton(
                "Park",
                icon=ft.Icons.PAUSE_CIRCLE,
                on_click=lambda e: self._run_task(self._disconnect(e)),
            ),
            ping_btn=ft.OutlinedButton("PING", on_click=lambda e: self._run_task(self._ping(e))),
            link_btn=ft.OutlinedButton("BS_LINK", on_click=lambda e: self._run_task(self._read_link(e))),
            snapshot_btn=ft.OutlinedButton(
                "Copy snapshot",
                icon=ft.Icons.BUG_REPORT,
                on_click=lambda e: self._run_task(self._copy_snapshot(e)),
            ),
            resume_btn=ft.FilledButton(
                "Resume auto",
                icon=ft.Icons.PLAY_CIRCLE,
                on_click=lambda e: self._run_task(self._resume_auto(e)),
            ),
            policy_text=self.policy_text,
            link_text=self.link_text,
            status_text=self.status_text,
            sensor_tiles=[self.sensor_tiles[k] for k in self.sensor_tiles],
        )

        self.log_page = LogPage(
            log_list=self.log_list,
            log_meta=self.log_meta,
            log_copy_status=self.log_copy_status,
            copy_log_btn=ft.OutlinedButton(
                "Copy log",
                icon=ft.Icons.CONTENT_COPY,
                on_click=lambda e: self._run_task(self._copy_log(e)),
            ),
            copy_snapshot_btn=ft.OutlinedButton(
                "Copy snapshot",
                icon=ft.Icons.BUG_REPORT,
                on_click=lambda e: self._run_task(self._copy_snapshot(e)),
            ),
            clear_btn=ft.OutlinedButton(
                "Clear",
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda e: self._run_task(self._clear_log(e)),
            ),
        )

        self.settings_page = SettingsPage(
            layout_preset=self.prefs.layout_preset,
            focus_sensor=self.prefs.focus_sensor,
            sidebar_collapsed=self.prefs.sidebar_collapsed,
            auto_switch=self.auto_switch,
            update_on_data_switch=self.update_on_data_switch,
            plot_modes=dict(self.prefs.plot_mode),
            on_layout=self._set_layout_preset,
            on_focus_sensor=self._set_focus_sensor,
            on_sidebar_mode=self._set_sidebar_collapsed,
            on_plot_mode=self._set_plot_mode_pref,
        )

        self.sidebar = SidebarNav(
            collapsed=self.prefs.sidebar_collapsed,
            active_route=self.prefs.active_route,
            phase_color_key="grey",
            device_name="No device",
            device_address=None,
            on_nav=self._navigate,
            on_toggle=self._toggle_sidebar,
        )

        self._top_bar = build_top_bar(
            route_title=ROUTE_LABELS.get(self.prefs.active_route, "Live"),
            trailing=self.auto_switch,
        )
        self._shell = AppShell(
            sidebar=self.sidebar,
            top_bar=self._top_bar,
            content=self._page_for_route(self.prefs.active_route),
        )

        self._rebuild_live_grid()

    def _build_scene_row(self) -> ft.Row:
        stream_btn = ft.FilledButton(
            "Stream on",
            icon=ft.Icons.PLAY_ARROW,
            on_click=lambda e: self._run_task(self._stream_on(e)),
        )
        return ft.Row(
            [
                ft.Text("Scene", size=11, color=TEXT_MUTED),
                ft.OutlinedButton("Motion", on_click=lambda e: self._run_task(self._apply_motion(e))),
                ft.OutlinedButton("Realtime", on_click=lambda e: self._run_task(self._apply_realtime(e))),
                ft.OutlinedButton("Lab Quiet", on_click=lambda e: self._run_task(self._apply_lab_quiet(e))),
                ft.OutlinedButton(
                    "Reset counts",
                    icon=ft.Icons.RESTART_ALT,
                    on_click=lambda e: self._run_task(self._reset_counts(e)),
                ),
                stream_btn,
            ],
            wrap=True,
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _page_for_route(self, route: str) -> ft.Control:
        if route == "connect":
            return self.connect_page.build()
        if route == "log":
            return self.log_page.build()
        if route == "settings":
            return self.settings_page.build()
        return self.live_page.build()

    def _navigate(self, route: str) -> None:
        self.prefs.active_route = route
        self.prefs_store.schedule_save()
        self.sidebar.update_state(active_route=route)
        self._top_bar.content.controls[0].value = ROUTE_LABELS.get(route, route)
        self._shell.set_page_content(self._page_for_route(route))
        self.page.update()

    def _toggle_sidebar(self) -> None:
        self.prefs.sidebar_collapsed = not self.prefs.sidebar_collapsed
        self.prefs_store.schedule_save()
        self.sidebar.update_state(collapsed=self.prefs.sidebar_collapsed)
        self.settings_page.update_state(sidebar_collapsed=self.prefs.sidebar_collapsed)
        self.page.update()

    def _set_layout_preset(self, preset: str) -> None:
        self.prefs.layout_preset = preset
        self.prefs_store.schedule_save()
        self.live_page.rebuild_toolbar(
            layout_preset=preset,
            focus_sensor=self.prefs.focus_sensor,
            on_layout=self._set_layout_preset,
            on_focus_sensor=self._set_focus_sensor,
            scene_row=self._scene_row,
        )
        self.settings_page.update_state(layout_preset=preset)
        self._rebuild_live_grid()
        if self.prefs.active_route == "live":
            self._shell.set_page_content(self.live_page.build())
        self.page.update()

    def _set_focus_sensor(self, sensor: str) -> None:
        self.prefs.focus_sensor = sensor
        self.prefs_store.schedule_save()
        self.live_page.rebuild_toolbar(
            layout_preset=self.prefs.layout_preset,
            focus_sensor=sensor,
            on_layout=self._set_layout_preset,
            on_focus_sensor=self._set_focus_sensor,
            scene_row=self._scene_row,
        )
        self.settings_page.update_state(focus_sensor=sensor)
        self._rebuild_live_grid()
        if self.prefs.active_route == "live":
            self._shell.set_page_content(self.live_page.build())
        self.page.update()

    def _set_sidebar_collapsed(self, collapsed: bool) -> None:
        if collapsed == self.prefs.sidebar_collapsed:
            return
        self.prefs.sidebar_collapsed = collapsed
        self.prefs_store.schedule_save()
        self.sidebar.update_state(collapsed=collapsed)
        self.settings_page.update_state(sidebar_collapsed=collapsed)
        self.page.update()

    def _set_plot_mode_pref(self, sensor: str, mode: str) -> None:
        self.prefs.plot_mode[sensor] = mode
        self.prefs_store.schedule_save()
        self.live_cards[sensor].set_plot_mode(mode)
        self.settings_page.update_state(plot_modes=dict(self.prefs.plot_mode))
        self.page.update()

    def _on_card_plot_mode(self, sensor: str, mode: str) -> None:
        self.prefs.plot_mode[sensor] = mode
        self.prefs_store.schedule_save()
        self.settings_page.update_state(plot_modes=dict(self.prefs.plot_mode))

    def _rebuild_live_grid(self) -> None:
        self.grid_host.rebuild(
            layout_preset=self.prefs.layout_preset,
            focus_sensor=self.prefs.focus_sensor,
            cards=self.live_cards,
        )

    def _run_task(self, coro) -> None:
        try:
            self.page.run_task(coro)
        except Exception:
            try:
                asyncio.get_running_loop().create_task(coro)
            except RuntimeError:
                pass

    def _cancel_ui_flush(self) -> None:
        task = self._ui_flush_task
        self._ui_flush_task = None
        if task is not None and not task.done():
            task.cancel()

    def _safe_page_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError as exc:
            if "destroyed session" in str(exc).lower():
                return
            raise

    def build(self) -> ft.Control:
        return self._shell

    def start(self) -> None:
        self._set_phase(ConnPhase.IDLE)
        self._on_log(
            "info",
            f"App start · Auto={'ON' if self.auto_enabled else 'OFF'} · "
            f"default_scene={self.last_preset_id} · last_addr={self.last_address or '-'}",
        )
        if self.auto_enabled:
            self._start_auto_loop(ConnPhase.HUNTING)

    def _connect_busy(self) -> bool:
        return self.phase in (ConnPhase.HUNTING, ConnPhase.CONNECTING, ConnPhase.RECOVERING)

    def _sync_connect_btn(self) -> None:
        self._connect_btn.disabled = self._connect_busy()

    def _set_phase(self, phase: ConnPhase) -> None:
        self.phase = phase
        name = self.session.state.device_name
        streaming = self.session.state.streaming
        label = phase_chip_label(
            phase,
            device_name=name,
            preset_id=self.last_preset_id,
            streaming=streaming,
        )
        color_key = phase_chip_color(phase)
        if phase is ConnPhase.HUNTING:
            self.live_hint.value = "Looking for TESAIoT-* ... will auto-connect when found."
        elif phase is ConnPhase.RECOVERING:
            self.live_hint.value = "Link lost - reconnecting and restoring stream..."
        elif phase is ConnPhase.CONNECTING:
            self.live_hint.value = "Connecting..."
        elif phase is ConnPhase.LINKED:
            self.live_hint.value = "Connected - starting stream..."
        elif phase is ConnPhase.LIVE:
            self.live_hint.value = f"Live sensors · scene {self.last_preset_id} · UI <=4 Hz"
        elif phase is ConnPhase.PARKED:
            self.live_hint.value = "Auto paused. Toggle Auto or Resume auto to hunt again."
        else:
            self.live_hint.value = "Enable Auto or Scan to find a board."

        st = self.session.state
        detail = st.device_name or "No device"
        if st.connected and st.device_address:
            detail = f"{st.device_name} · {st.device_address}"
        meta = (
            f"policy 0x{st.policy_flags:02x} · evt {sum(st.frame_unique.values())} · "
            f"scene {self.last_preset_id}"
        )
        show_stream = (
            phase is ConnPhase.LINKED
            and st.connected
            and st.policy_flags != _BLE_POLICY_STREAMING
        )
        self.hero.update(
            chip_label=label,
            chip_color_key=color_key,
            detail=detail,
            meta=meta,
            show_stream_on=show_stream,
        )
        self.sidebar.update_state(
            phase_color_key=color_key,
            device_name=st.device_name or self.last_device_name or "No device",
            device_address=st.device_address or self.last_address,
        )
        self._sync_connect_btn()
        self._chrome_dirty = True

    def _cancel_auto_loop(self) -> None:
        self._auto_gen += 1
        task = self._auto_task
        self._auto_task = None
        if task is not None and not task.done():
            task.cancel()

    def _start_auto_loop(self, phase: ConnPhase) -> None:
        if not self.auto_enabled and phase not in (ConnPhase.PARKED, ConnPhase.IDLE):
            return
        self._cancel_auto_loop()
        self._set_phase(phase)
        gen = self._auto_gen

        async def runner() -> None:
            try:
                await self._auto_supervisor(gen)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self._on_log("error", f"Auto loop: {exc!r}")
                if self.auto_enabled:
                    self._set_phase(ConnPhase.HUNTING)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._on_log("warn", "Auto: waiting for event loop")
            return
        self._auto_task = loop.create_task(runner())

    async def _auto_supervisor(self, gen: int) -> None:
        while gen == self._auto_gen and self.auto_enabled:
            if self.phase is ConnPhase.PARKED:
                return
            if self.phase is ConnPhase.LIVE and self.session.connected:
                await asyncio.sleep(0.5)
                continue
            if self.phase is ConnPhase.RECOVERING:
                await asyncio.sleep(RECOVER_GRACE_S)
                if gen != self._auto_gen or not self.auto_enabled:
                    return
                self._set_phase(ConnPhase.HUNTING)

            if self.phase is ConnPhase.HUNTING:
                ok = await self._hunt_once()
                if gen != self._auto_gen:
                    return
                if not ok:
                    delay = HUNT_BACKOFF_S[min(self._hunt_fails, len(HUNT_BACKOFF_S) - 1)]
                    self._hunt_fails += 1
                    await asyncio.sleep(delay)
                    continue
                self._hunt_fails = 0
                continue

            if self.phase in (ConnPhase.CONNECTING, ConnPhase.LINKED):
                await asyncio.sleep(0.2)
                continue

            if self.phase is ConnPhase.IDLE and self.auto_enabled:
                self._set_phase(ConnPhase.HUNTING)
                continue

            await asyncio.sleep(0.3)

    async def _hunt_once(self) -> bool:
        self._on_log(
            "info",
            f"Auto hunt · prefer={self.last_device_name or self.last_address or 'best-RSSI'} · "
            f"fails={self._hunt_fails} · scene={self.last_preset_id}",
        )
        try:
            ranked = await self.session.scan_ranked(timeout=12.0)
        except Exception as exc:
            self._on_log("error", f"Auto scan failed: {exc!r}")
            return False

        self.devices = [d for d, _ in ranked]
        self.device_dropdown.options = [
            ft.dropdown.Option(key=d.address, text=f"{d.name or 'TESAIoT'} ({d.address})")
            for d in self.devices
        ]
        self.device_dropdown.disabled = len(self.devices) == 0

        if ranked:
            preview = ", ".join(
                f"{(d.name or 'TESAIoT')}:{d.address} rssi={rssi}" for d, rssi in ranked[:5]
            )
            self._on_log("info", f"Scan hit {len(ranked)}: {preview}")

        device = self._pick_device(ranked)
        if device is None:
            self._on_log("info", "Auto: no TESAIoT peripheral yet — will backoff and retry")
            self.page.update()
            return False

        rssi = next((r for d, r in ranked if d.address == device.address), "?")
        pick_key = device_identity_key(name=device.name, address=device.address)
        prefer_key = self.last_device_name or self.last_address
        if prefer_key and pick_key == prefer_key:
            why = "last_identity"
        elif self.last_device_name and device.name == self.last_device_name:
            why = "last_name"
        elif self.last_address and device.address == self.last_address:
            why = "last_address"
        else:
            why = "best_rssi"
        if (
            self.last_address
            and device.address != self.last_address
            and self.last_device_name
            and device.name == self.last_device_name
        ):
            self._on_log(
                "info",
                f"BLE address rotated {self.last_address} → {device.address} "
                f"(same {device.name})",
            )
        self._on_log(
            "info",
            f"Auto pick {device.name or 'TESAIoT'} {device.address} rssi={rssi} ({why})",
        )
        self.device_dropdown.value = device.address
        self.page.update()
        return await self._connect_and_go_live(device, source="auto")

    def _pick_device(self, ranked: list[tuple[BLEDevice, int]]) -> BLEDevice | None:
        if not ranked:
            return None
        if self.last_device_name:
            for device, _rssi in ranked:
                if device.name == self.last_device_name:
                    return device
        if self.last_address:
            for device, _rssi in ranked:
                if device.address == self.last_address:
                    return device
        return ranked[0][0]

    async def _connect_and_go_live(self, device: BLEDevice, *, source: str) -> bool:
        self._set_phase(ConnPhase.CONNECTING)
        self._on_log(
            "info",
            f"Connect begin · source={source} · {device.name or 'TESAIoT'} {device.address} · "
            f"phase→connecting",
        )
        self.page.update()
        try:
            await self.session.connect(device, bootstrap="fast")
        except Exception as exc:
            self._on_log("error", f"Connect failed ({source}): {exc!r}")
            if self.auto_enabled and source == "auto":
                self._set_phase(ConnPhase.HUNTING)
            else:
                self._set_phase(ConnPhase.IDLE)
            self.page.update()
            return False

        self.last_address = device.address
        self.last_device_name = device.name or self.last_device_name
        self._set_phase(ConnPhase.LINKED)
        st = self.session.state
        scene_id = AUTO_STREAM_SCENE_PRESET
        self._on_log(
            "info",
            f"Linked · policy=0x{st.policy_flags:02x} · link state={st.link_state} mtu={st.link_mtu} · "
            f"Stream on first · then scene={scene_id}",
        )
        self.page.update()
        stream_ok = False
        try:
            await self.session.enable_streaming(refresh_cfg=False)
            stream_ok = self.session.state.streaming
            self._on_log("info", f"Stream on early · policy=0x{self.session.state.policy_flags:02x}")
        except Exception as exc:
            self._on_log("warn", f"Stream on early failed: {exc!r} — will retry after preset")
        try:
            try:
                line = await self.session.apply_scene_preset(scene_id, go_live=True)
                self.last_preset_id = scene_id
                self._on_log("info", f"Scene OK · {line}")
            except Exception as exc:
                self._on_log("warn", f"Scene {scene_id} failed: {exc!r}")
            if not stream_ok:
                await self.session.enable_streaming()
            self.session.reset_frame_counts()
            self._set_phase(ConnPhase.LIVE)
            self._navigate("live")
            st = self.session.state
            self._on_log(
                "info",
                f"LIVE · policy=0x{st.policy_flags:02x} streaming={st.streaming} · "
                f"Auto={self.auto_enabled} · scene={self.last_preset_id}",
            )
            self._flush_ui(force=True)
            self.page.update()
            return True
        except Exception as exc:
            self._on_log("error", f"Stream / go-live failed: {exc!r}")
            if self.auto_enabled:
                self._set_phase(ConnPhase.HUNTING)
            else:
                self._set_phase(ConnPhase.LINKED)
            self.page.update()
            return False

    async def _on_link_lost(self) -> None:
        self._cancel_ui_flush()
        self._pending_samples.clear()
        st_note = (
            f"Auto={'ON' if self.auto_enabled else 'OFF'} · last={self.last_device_name or self.last_address or '-'} · "
            f"preset={self.last_preset_id} · prior_phase={self.phase.value} · "
            f"peak_deviceMs={self.session.peak_device_ms}"
        )
        if not self.auto_enabled:
            self._on_log("warn", f"Link lost · Auto off — staying idle ({st_note})")
            self._set_phase(ConnPhase.IDLE)
            self._flush_ui(force=True)
            return
        if self.phase is ConnPhase.PARKED:
            self._on_log("warn", f"Link lost while Parked — not hunting ({st_note})")
            return
        self._on_log("warn", f"Link lost · RECOVERING ({st_note})")
        self._start_auto_loop(ConnPhase.RECOVERING)

    def _apply_stats_to_control(self, key: str) -> None:
        line = self.session.frame_stats_line(key)
        ok: bool | None = None
        if "MISMATCH" in line:
            ok = False
        elif "[OK]" in line:
            ok = True
        ctrl = self.sensor_stats[key]
        if ok is True:
            ctrl.color = ft.Colors.GREEN_300
        elif ok is False:
            ctrl.color = ft.Colors.ORANGE_300
        else:
            ctrl.color = ft.Colors.CYAN_200
        ctrl.value = line
        self.live_cards[key].set_stats(line, ok=ok)

    def _ui_paint_mode_label(self) -> str:
        if self.update_on_data:
            return "UI on each EVT"
        return f"UI <={1.0 / _UI_PAINT_INTERVAL_S:.0f} Hz"

    def _refresh_window_line(self) -> None:
        window_s = self.session.count_window_seconds()
        total_u = sum(self.session.state.frame_unique.values())
        total_r = sum(self.session.state.frame_raw.values())
        self.window_text.value = (
            f"count window {window_s:.1f}s · evt total={total_u} · raw total={total_r} · "
            f"{self._ui_paint_mode_label()}"
        )

    def _paint_sensor_sample(self, sample: dict) -> None:
        key = sample["sensor"]
        meta = self.session.format_sample_meta(sample)
        self.sensor_meta[key].value = meta
        self.sensor_values[key].value = _fmt_fields(sample.get("fields", {}))
        self.live_cards[key].set_badge(meta)
        self.live_cards[key].apply_sample(sample)
        if self.live_cards[key].plot_mode == "lines":
            self.live_cards[key].refresh_charts()
        self._apply_stats_to_control(key)

    def _flush_ui(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if (
            not force
            and not self.update_on_data
            and (now - self._last_ui_paint_s) < _UI_PAINT_INTERVAL_S
        ):
            self._schedule_ui_flush()
            return
        self._last_ui_paint_s = now
        pending = self._pending_samples
        self._pending_samples = {}
        for sample in pending.values():
            self._paint_sensor_sample(sample)
        for key in self.sensor_stats:
            if key not in pending:
                self._apply_stats_to_control(key)
        self._refresh_window_line()
        if self.phase is ConnPhase.LIVE:
            self._set_phase(ConnPhase.LIVE)
        if self._chrome_dirty:
            self._chrome_dirty = False
        self._safe_page_update()

    def _schedule_ui_flush(self) -> None:
        if self.update_on_data:
            self._flush_ui(force=True)
            return
        if self._ui_flush_task is not None and not self._ui_flush_task.done():
            return

        async def _delayed() -> None:
            try:
                await asyncio.sleep(_UI_PAINT_INTERVAL_S)
                self._flush_ui(force=True)
            except asyncio.CancelledError:
                return
            except RuntimeError as exc:
                if "destroyed session" in str(exc).lower():
                    return
                raise

        try:
            self._ui_flush_task = asyncio.get_running_loop().create_task(_delayed())
        except RuntimeError:
            self._flush_ui(force=True)

    def _refresh_log_meta(self) -> None:
        self.log_meta.value = f"{len(self._log_lines)} lines (max {_LOG_MAX_LINES})"

    def _append_log_line(self, line: str, *, color) -> None:
        self._log_lines.append(line)
        self.log_list.controls.append(
            ft.Text(line, size=11, color=color, selectable=True),
        )
        while len(self._log_lines) > _LOG_MAX_LINES:
            self._log_lines.pop(0)
            if self.log_list.controls:
                self.log_list.controls.pop(0)
        self._refresh_log_meta()

    def _on_log(self, level: str, text: str) -> None:
        color = ft.Colors.GREY_300
        if level == "error":
            color = ft.Colors.RED_300
        elif level == "warn":
            color = ft.Colors.AMBER_200
        elif level == "info":
            color = ft.Colors.GREEN_200
        elif level == "debug":
            color = ft.Colors.BLUE_GREY_200
        line = format_log_line(level, text)
        self._append_log_line(line, color=color)
        try:
            self._safe_page_update()
        except Exception:
            pass

    def _build_plain_log_text(self) -> str:
        header = build_session_snapshot(
            phase=self.phase.value,
            auto_enabled=self.auto_enabled,
            last_address=self.last_address,
            last_device_name=self.last_device_name,
            last_preset_id=self.last_preset_id,
            hunt_fails=self._hunt_fails,
            state=self.session.state,
            frame_stats_lines={k: self.session.frame_stats_line(k) for k in ("bmi270", "bmm350", "sht40", "dps368")},
            count_window_s=self.session.count_window_seconds(),
            note="prepended when copying full log",
        )
        body = "\n".join(self._log_lines) if self._log_lines else "(log empty)"
        return f"{header}\n\n--- log ---\n{body}\n"

    async def _copy_to_clipboard(self, text: str, *, ok_msg: str) -> None:
        try:
            await self.page.clipboard.set(text)
            self.log_copy_status.value = ok_msg
            self.log_copy_status.color = ft.Colors.GREEN_300
            line = format_log_line("info", f"Clipboard OK · {ok_msg} · {len(text)} chars")
            self._append_log_line(line, color=ft.Colors.GREEN_200)
        except Exception as exc:
            self.log_copy_status.value = f"Copy failed: {exc!r}"
            self.log_copy_status.color = ft.Colors.RED_300
            self._on_log("error", f"Clipboard set failed: {exc!r}")
        self.page.update()

    async def _copy_log(self, _e: ft.ControlEvent) -> None:
        await self._copy_to_clipboard(
            self._build_plain_log_text(),
            ok_msg="Copied log + snapshot — paste into chat",
        )

    async def _copy_snapshot(self, _e: ft.ControlEvent) -> None:
        snap = build_session_snapshot(
            phase=self.phase.value,
            auto_enabled=self.auto_enabled,
            last_address=self.last_address,
            last_device_name=self.last_device_name,
            last_preset_id=self.last_preset_id,
            hunt_fails=self._hunt_fails,
            state=self.session.state,
            frame_stats_lines={k: self.session.frame_stats_line(k) for k in ("bmi270", "bmm350", "sht40", "dps368")},
            count_window_s=self.session.count_window_seconds(),
            note="snapshot only (no log body)",
        )
        await self._copy_to_clipboard(snap, ok_msg="Copied snapshot — paste into chat")

    async def _clear_log(self, _e: ft.ControlEvent) -> None:
        self._log_lines.clear()
        self.log_list.controls.clear()
        self.log_copy_status.value = ""
        self._refresh_log_meta()
        self._on_log("info", "Log cleared")
        self.page.update()

    def _on_sample(self, sample: dict) -> None:
        self._pending_samples[sample["sensor"]] = sample
        if self.update_on_data:
            self._flush_ui(force=True)
            return
        now = time.monotonic()
        if (now - self._last_ui_paint_s) >= _UI_PAINT_INTERVAL_S:
            self._flush_ui(force=True)
        else:
            self._schedule_ui_flush()

    def _on_update_on_data_toggle(self, e: ft.ControlEvent) -> None:
        self.update_on_data = bool(e.control.value)
        self.prefs.update_on_data = self.update_on_data
        self.prefs_store.schedule_save()
        task = self._ui_flush_task
        self._ui_flush_task = None
        if task is not None and not task.done():
            task.cancel()
        mode = "each EVT" if self.update_on_data else f"throttled ~{1.0 / _UI_PAINT_INTERVAL_S:.0f} Hz"
        self._on_log("info", f"UI paint mode · {mode}")
        self._refresh_window_line()
        self._flush_ui(force=True)
        self.page.update()

    def _on_state(self, state: SessionState) -> None:
        if state.connected:
            self.status_text.value = f"Connected — {state.device_name} ({state.device_address})"
            self.status_text.color = ft.Colors.GREEN_300
        else:
            self.status_text.value = "Disconnected"
            self.status_text.color = ft.Colors.GREY_400
        pol = state.policy_flags
        self.policy_text.value = (
            f"policy 0x{pol:02x} "
            f"({'TX_EVT' if pol & 0x02 else 'no EVT'})"
            f"{' · streaming' if state.streaming else ''}"
            f" · scene {self.last_preset_id}"
        )
        self.link_text.value = (
            f"BS_LINK state={state.link_state} mtu={state.link_mtu} tx_drops={state.link_tx_drops}"
        )
        self._chrome_dirty = True
        if state.streaming and self._pending_samples:
            self._schedule_ui_flush()
        else:
            for key in self.sensor_stats:
                self._apply_stats_to_control(key)
            self._refresh_window_line()
            try:
                self.page.update()
            except Exception:
                pass

    def _on_auto_toggle(self, e: ft.ControlEvent) -> None:
        self.auto_enabled = bool(e.control.value)
        self.prefs.auto_enabled = self.auto_enabled
        self.prefs_store.schedule_save()
        if self.auto_enabled:
            if self.session.connected and self.session.state.streaming:
                self._set_phase(ConnPhase.LIVE)
                self._start_auto_loop(ConnPhase.LIVE)
            elif self.session.connected:
                self._set_phase(ConnPhase.LINKED)
                self._cancel_auto_loop()
                asyncio.create_task(self._go_live_then_watch())
            else:
                self._hunt_fails = 0
                self._start_auto_loop(ConnPhase.HUNTING)
            self._on_log("info", "Auto ON — hunt / restore enabled")
        else:
            self._cancel_auto_loop()
            if self.session.connected:
                self._set_phase(ConnPhase.LIVE if self.session.state.streaming else ConnPhase.LINKED)
            else:
                self._set_phase(ConnPhase.PARKED)
            self._on_log("info", "Auto OFF — manual mode (no hunt on disconnect)")
        self.page.update()

    async def _go_live_then_watch(self) -> None:
        await self._go_live_existing()
        if self.auto_enabled and self.session.connected:
            self._start_auto_loop(ConnPhase.LIVE)

    async def _go_live_existing(self) -> None:
        if not self.session.connected:
            return
        scene_id = AUTO_STREAM_SCENE_PRESET
        try:
            try:
                line = await self.session.apply_scene_preset(scene_id)
                self.last_preset_id = scene_id
                self._on_log("info", f"Scene OK · {line}")
            except Exception as exc:
                self._on_log("warn", f"Scene {scene_id} failed: {exc!r}")
            await self.session.enable_streaming()
            self.session.reset_frame_counts()
            self._set_phase(ConnPhase.LIVE)
            self._navigate("live")
            self._flush_ui(force=True)
            self._on_log(
                "info",
                f"LIVE (existing link) · streaming={self.session.state.streaming} · scene={scene_id}",
            )
        except Exception as exc:
            self._on_log("error", f"Go-live failed: {exc!r}")
            if self.auto_enabled:
                self._start_auto_loop(ConnPhase.HUNTING)

    async def _resume_auto(self, _e: ft.ControlEvent) -> None:
        self.auto_enabled = True
        self.auto_switch.value = True
        self.prefs.auto_enabled = True
        self.prefs_store.schedule_save()
        self._hunt_fails = 0
        self._on_log("info", f"Resume auto · prefer={self.last_address or 'best-RSSI'} · scene={self.last_preset_id}")
        self._start_auto_loop(ConnPhase.HUNTING)
        self.page.update()

    async def _scan(self, _e: ft.ControlEvent) -> None:
        self._on_log("info", "Manual scan for TESAIoT-* ...")
        try:
            ranked = await self.session.scan_ranked(timeout=8.0)
        except Exception as exc:
            self._on_log("error", f"Scan failed: {exc!r}")
            return
        self.devices = [d for d, _ in ranked]
        self.device_dropdown.options = [
            ft.dropdown.Option(key=d.address, text=f"{d.name or 'TESAIoT'} ({d.address})")
            for d in self.devices
        ]
        self.device_dropdown.disabled = len(self.devices) == 0
        if ranked:
            preview = ", ".join(
                f"{(d.name or 'TESAIoT')}:{d.address} rssi={rssi}" for d, rssi in ranked[:5]
            )
            self._on_log("info", f"Scan hit {len(ranked)}: {preview}")
        else:
            self._on_log("warn", "Scan: no TESAIoT peripherals")
        if self.devices:
            pick = self._pick_device(ranked)
            self.device_dropdown.value = pick.address if pick else self.devices[0].address
            if self.auto_enabled and not self.session.connected:
                device = pick or self.devices[0]
                await self._connect_and_go_live(device, source="scan")
                if self.auto_enabled:
                    self._start_auto_loop(ConnPhase.LIVE if self.session.connected else ConnPhase.HUNTING)
        self.page.update()

    def _device_by_address(self, address: str | None) -> BLEDevice | None:
        if not address:
            return None
        for device in self.devices:
            if device.address == address:
                return device
        return None

    async def _read_link(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.read_link_snapshot()
            st = self.session.state
            self._on_log(
                "info",
                f"BS_LINK · state={st.link_state} mtu={st.link_mtu} tx_drops={st.link_tx_drops}",
            )
        except Exception as exc:
            self._on_log("error", f"BS_LINK read failed: {exc!r}")

    async def _stream_on(self, _e: ft.ControlEvent) -> None:
        if not self.session.connected:
            self._on_log("error", "Connect first, then Stream on")
            return
        try:
            await self.session.enable_streaming()
            st = self.session.state
            self._set_phase(ConnPhase.LIVE)
            self._navigate("live")
            self._flush_ui(force=True)
            self._on_log(
                "info",
                f"Stream on · policy=0x{st.policy_flags:02x} streaming={st.streaming} · counters reset",
            )
        except Exception as exc:
            self._on_log("error", f"Stream on failed: {exc!r}")

    async def _apply_preset(self, preset_id: str) -> None:
        if not self.session.connected:
            self._on_log("error", "Connect first, then apply a preset")
            return
        try:
            line = await self.session.apply_scene_preset(preset_id)
            self.last_preset_id = preset_id
            self.session.reset_frame_counts()
            if self.session.state.streaming:
                self._set_phase(ConnPhase.LIVE)
            self._flush_ui(force=True)
            self._on_log(
                "info",
                f"Preset applied · id={preset_id} · {line} · remembered for Auto restore",
            )
        except Exception as exc:
            self._on_log("error", f"Preset {preset_id} failed: {exc!r}")

    async def _apply_motion(self, _e: ft.ControlEvent) -> None:
        await self._apply_preset("motion")

    async def _apply_realtime(self, _e: ft.ControlEvent) -> None:
        await self._apply_preset("realtime")

    async def _apply_lab_quiet(self, _e: ft.ControlEvent) -> None:
        await self._apply_preset("labQuiet")

    async def _reset_counts(self, _e: ft.ControlEvent) -> None:
        self.session.reset_frame_counts()
        self._flush_ui(force=True)
        self._on_log("info", "Frame counters reset · rate window restarted")

    async def _ping(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.ping()
            self._on_log("info", "PING OK")
        except Exception as exc:
            self._on_log("error", f"PING failed: {exc!r}")

    async def _connect(self, _e: ft.ControlEvent) -> None:
        if self._connect_busy():
            self._on_log("warn", "Connect blocked while Auto is hunting / connecting / recovering")
            return
        self._cancel_auto_loop()
        device = self._device_by_address(self.device_dropdown.value)
        if device is None:
            self._on_log("error", "Select a peripheral after Scan")
            return
        ok = await self._connect_and_go_live(device, source="manual")
        if ok and self.auto_enabled:
            self._start_auto_loop(ConnPhase.LIVE)

    async def _disconnect(self, _e: ft.ControlEvent) -> None:
        self._cancel_auto_loop()
        self.auto_enabled = False
        self.auto_switch.value = False
        self.prefs.auto_enabled = False
        self.prefs_store.schedule_save()
        self._on_log(
            "info",
            f"User Park → Auto off · was phase={self.phase.value} · addr={self.last_address or '-'}",
        )
        await self.session.disconnect(user_initiated=True)
        self._pending_samples.clear()
        self._set_phase(ConnPhase.PARKED)
        self._flush_ui(force=True)
        self._on_log("info", "Parked — enable Auto or Resume auto to hunt again")
        self.page.update()
