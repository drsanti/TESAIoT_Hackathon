"""Settings page — layout, plots, sidebar, defaults."""

from __future__ import annotations

import flet as ft

from bs2.decode import SENSOR_LABELS
from ui.preferences import SENSOR_KEYS
from ui.theme import BORDER, CARD, TEXT_MUTED, segmented_chips


class SettingsPage:
    def __init__(
        self,
        *,
        layout_preset: str,
        focus_sensor: str,
        sidebar_collapsed: bool,
        auto_switch: ft.Switch,
        update_on_data_switch: ft.Switch,
        plot_modes: dict[str, str],
        on_layout,
        on_focus_sensor,
        on_sidebar_mode,
        on_plot_mode,
    ) -> None:
        self._layout_preset = layout_preset
        self._focus_sensor = focus_sensor
        self._sidebar_collapsed = sidebar_collapsed
        self._auto_switch = auto_switch
        self._update_switch = update_on_data_switch
        self._plot_modes = plot_modes
        self._on_layout = on_layout
        self._on_focus_sensor = on_focus_sensor
        self._on_sidebar_mode = on_sidebar_mode
        self._on_plot_mode = on_plot_mode
        self._focus_dd = ft.Dropdown(
            width=180,
            value=focus_sensor,
            options=[ft.dropdown.Option(key=k, text=SENSOR_LABELS.get(k, k)) for k in SENSOR_KEYS],
            on_select=lambda e: self._on_focus_sensor(e.control.value or "bmi270"),
        )
        self._layout_host = ft.Container()
        self._sidebar_host = ft.Container()
        self._plot_hosts: dict[str, ft.Container] = {}
        self._sync_controls()

    def _sync_controls(self) -> None:
        self._layout_host.content = segmented_chips(
            [("grid", "Grid"), ("stack", "Stack"), ("focus", "Focus")],
            self._layout_preset,
            self._on_layout,
        )
        self._focus_dd.value = self._focus_sensor
        self._focus_dd.visible = self._layout_preset == "focus"
        mode = "collapsed" if self._sidebar_collapsed else "expanded"
        self._sidebar_host.content = segmented_chips(
            [("expanded", "Expanded"), ("collapsed", "Collapsed")],
            mode,
            lambda k: self._on_sidebar_mode(k == "collapsed"),
        )
        for key in SENSOR_KEYS:
            host = self._plot_hosts.get(key)
            if host is None:
                host = ft.Container()
                self._plot_hosts[key] = host
            host.content = segmented_chips(
                [("bars", "Bars"), ("lines", "Lines")],
                self._plot_modes.get(key, "bars"),
                lambda m, sk=key: self._on_plot_mode(sk, m),
                dense=True,
            )

    def update_state(
        self,
        *,
        layout_preset: str | None = None,
        focus_sensor: str | None = None,
        sidebar_collapsed: bool | None = None,
        plot_modes: dict[str, str] | None = None,
    ) -> None:
        if layout_preset is not None:
            self._layout_preset = layout_preset
        if focus_sensor is not None:
            self._focus_sensor = focus_sensor
        if sidebar_collapsed is not None:
            self._sidebar_collapsed = sidebar_collapsed
        if plot_modes is not None:
            self._plot_modes = plot_modes
        self._sync_controls()

    def build(self) -> ft.Control:
        plot_rows = [
            ft.Row(
                [
                    ft.Text(SENSOR_LABELS.get(k, k), size=12, width=80),
                    self._plot_hosts[k],
                ],
                spacing=12,
            )
            for k in SENSOR_KEYS
        ]
        return ft.Column(
            [
                ft.Container(
                    bgcolor=CARD,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("Layout preset", size=12, weight=ft.FontWeight.W_600),
                            self._layout_host,
                            ft.Text("Focus sensor", size=11, color=TEXT_MUTED),
                            self._focus_dd,
                        ],
                        spacing=8,
                    ),
                ),
                ft.Container(
                    bgcolor=CARD,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("Defaults", size=12, weight=ft.FontWeight.W_600),
                            self._auto_switch,
                            self._update_switch,
                            ft.Text("Sidebar", size=11, color=TEXT_MUTED),
                            self._sidebar_host,
                        ],
                        spacing=8,
                    ),
                ),
                ft.Container(
                    bgcolor=CARD,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("Per-sensor default plot", size=12, weight=ft.FontWeight.W_600),
                            *plot_rows,
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
