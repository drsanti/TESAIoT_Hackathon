"""Settings page — layout, plots, sidebar, defaults."""

from __future__ import annotations

import flet as ft

from bs2.decode import SENSOR_LABELS
from ui.preferences import SENSOR_KEYS
from ui.theme import (
    ACCENT,
    BORDER,
    CARD,
    SENSOR_STRIPE,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    card_shell,
    segmented_chips,
)


def _section_title(title: str, subtitle: str | None = None) -> ft.Control:
    controls: list[ft.Control] = [
        ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT),
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=11, color=TEXT_MUTED))
    return ft.Column(controls, spacing=2)


def _toggle_row(
    *,
    title: str,
    hint: str,
    switch: ft.Switch,
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(title, size=13, weight=ft.FontWeight.W_500, color=TEXT),
                        ft.Text(hint, size=11, color=TEXT_MUTED),
                    ],
                    spacing=2,
                    expand=True,
                ),
                switch,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=10,
    )


def _field_block(label: str, control: ft.Control) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
            control,
        ],
        spacing=8,
    )


class SettingsPage:
    def __init__(
        self,
        *,
        layout_preset: str,
        focus_sensor: str,
        sidebar_collapsed: bool,
        auto_enabled: bool,
        update_on_data: bool,
        plot_modes: dict[str, str],
        on_layout,
        on_focus_sensor,
        on_sidebar_mode,
        on_plot_mode,
        on_auto_change,
        on_update_on_data_change,
    ) -> None:
        self._layout_preset = layout_preset
        self._focus_sensor = focus_sensor
        self._sidebar_collapsed = sidebar_collapsed
        self._plot_modes = dict(plot_modes)
        self._on_layout = on_layout
        self._on_focus_sensor = on_focus_sensor
        self._on_sidebar_mode = on_sidebar_mode
        self._on_plot_mode = on_plot_mode

        self._auto_switch = ft.Switch(
            value=auto_enabled,
            active_color=ACCENT,
            on_change=lambda e: on_auto_change(bool(e.control.value)),
        )
        self._update_switch = ft.Switch(
            value=update_on_data,
            active_color=ACCENT,
            on_change=lambda e: on_update_on_data_change(bool(e.control.value)),
        )
        self._focus_dd = ft.Dropdown(
            width=220,
            dense=True,
            border_color=BORDER,
            focused_border_color=ACCENT,
            value=focus_sensor,
            options=[ft.dropdown.Option(key=k, text=SENSOR_LABELS.get(k, k)) for k in SENSOR_KEYS],
            on_select=lambda e: self._on_focus_sensor(e.control.value or "bmi270"),
        )
        self._layout_host = ft.Container()
        self._sidebar_host = ft.Container()
        self._plot_hosts: dict[str, ft.Container] = {k: ft.Container() for k in SENSOR_KEYS}
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
            self._plot_hosts[key].content = segmented_chips(
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
        auto_enabled: bool | None = None,
        update_on_data: bool | None = None,
    ) -> None:
        if layout_preset is not None:
            self._layout_preset = layout_preset
        if focus_sensor is not None:
            self._focus_sensor = focus_sensor
        if sidebar_collapsed is not None:
            self._sidebar_collapsed = sidebar_collapsed
        if plot_modes is not None:
            self._plot_modes = dict(plot_modes)
        if auto_enabled is not None:
            self._auto_switch.value = auto_enabled
        if update_on_data is not None:
            self._update_switch.value = update_on_data
        self._sync_controls()
        if hasattr(self, "_focus_block"):
            self._focus_block.visible = self._layout_preset == "focus"

    def _layout_card(self) -> ft.Control:
        focus_block = ft.Column(
            [
                ft.Text("Focus sensor", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                self._focus_dd,
                ft.Text(
                    "Used when layout is Focus — one large card, others compact.",
                    size=11,
                    color=TEXT_MUTED,
                ),
            ],
            spacing=8,
            visible=self._layout_preset == "focus",
        )
        # Keep a stable host so visibility updates on rebuild.
        self._focus_block = focus_block
        return card_shell(
            ft.Column(
                [
                    _section_title("Live layout", "How sensor cards are arranged on Live"),
                    ft.Container(height=4),
                    _field_block("Preset", self._layout_host),
                    focus_block,
                ],
                spacing=10,
            ),
            padding=18,
        )

    def _behavior_card(self) -> ft.Control:
        return card_shell(
            ft.Column(
                [
                    _section_title("Behavior", "Connection hunt and Live refresh"),
                    ft.Container(height=4),
                    _toggle_row(
                        title="Auto hunt",
                        hint="Scan, connect, and start streaming without taps",
                        switch=self._auto_switch,
                    ),
                    _toggle_row(
                        title="Update on data",
                        hint="Repaint Live on every EVT (higher CPU)",
                        switch=self._update_switch,
                    ),
                    ft.Container(height=2),
                    _field_block("Sidebar", self._sidebar_host),
                ],
                spacing=10,
            ),
            padding=18,
        )

    def _plots_card(self) -> ft.Control:
        rows: list[ft.Control] = []
        for key in SENSOR_KEYS:
            stripe = SENSOR_STRIPE.get(key, ACCENT)
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=4,
                                height=28,
                                bgcolor=stripe,
                                border_radius=2,
                            ),
                            ft.Text(
                                SENSOR_LABELS.get(key, key),
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=TEXT,
                                width=90,
                            ),
                            ft.Container(expand=True),
                            self._plot_hosts[key],
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    bgcolor=SURFACE,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                )
            )
        return card_shell(
            ft.Column(
                [
                    _section_title(
                        "Sensor plots",
                        "Default Bars / Lines mode for each Live card",
                    ),
                    ft.Container(height=4),
                    ft.ResponsiveRow(
                        [
                            ft.Container(rows[0], col={"xs": 12, "md": 6}),
                            ft.Container(rows[1], col={"xs": 12, "md": 6}),
                            ft.Container(rows[2], col={"xs": 12, "md": 6}),
                            ft.Container(rows[3], col={"xs": 12, "md": 6}),
                        ],
                        spacing=10,
                        run_spacing=10,
                    ),
                ],
                spacing=10,
            ),
            padding=18,
        )

    def build(self) -> ft.Control:
        self._sync_controls()
        if hasattr(self, "_focus_block"):
            self._focus_block.visible = self._layout_preset == "focus"
        layout = self._layout_card()
        behavior = self._behavior_card()
        plots = self._plots_card()
        return ft.Column(
            [
                ft.Text(
                    "Tune Live layout and connection defaults. Changes save automatically.",
                    size=12,
                    color=TEXT_MUTED,
                ),
                ft.ResponsiveRow(
                    [
                        ft.Container(layout, col={"xs": 12, "md": 6}),
                        ft.Container(behavior, col={"xs": 12, "md": 6}),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                plots,
            ],
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
