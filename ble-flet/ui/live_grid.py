"""Layout preset host for sensor live cards."""

from __future__ import annotations

import flet as ft

from ui.live_widgets import SensorLiveCard
from ui.preferences import SENSOR_KEYS
from ui.theme import TEXT_MUTED


class LiveGridHost(ft.Container):
    def __init__(self) -> None:
        self._host = ft.Column(spacing=10, expand=True)
        super().__init__(content=self._host, expand=True)

    def rebuild(
        self,
        *,
        layout_preset: str,
        focus_sensor: str,
        cards: dict[str, SensorLiveCard],
        compact_keys: set[str] | None = None,
    ) -> None:
        compact_keys = compact_keys or set()
        ordered = list(SENSOR_KEYS)

        if layout_preset == "stack":
            self._host.controls = [
                ft.Container(cards[k], expand=False) for k in ordered
            ]
            return

        if layout_preset == "focus":
            focus = focus_sensor if focus_sensor in cards else "bmi270"
            others = [k for k in ordered if k != focus]
            mini_row = ft.ResponsiveRow(
                [
                    ft.Container(
                        cards[k],
                        col={"xs": 12, "sm": 4},
                    )
                    for k in others
                ],
                spacing=8,
                run_spacing=8,
            )
            for k in others:
                cards[k].set_compact(True)
            cards[focus].set_compact(False)
            self._host.controls = [
                ft.Container(cards[focus], expand=False),
                mini_row,
            ]
            return

        # grid (default)
        for k in ordered:
            cards[k].set_compact(False)
        self._host.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(cards[k], col={"xs": 12, "md": 6})
                    for k in ordered
                ],
                spacing=10,
                run_spacing=10,
            )
        ]


def layout_toolbar_row(
    *,
    layout_preset: str,
    focus_sensor: str,
    on_layout,
    on_focus_sensor,
    scene_row: ft.Control,
) -> ft.Column:
    from ui.theme import segmented_chips
    from bs2.decode import SENSOR_LABELS

    focus_dd = ft.Dropdown(
        width=140,
        value=focus_sensor,
        options=[
            ft.dropdown.Option(key=k, text=SENSOR_LABELS.get(k, k))
            for k in SENSOR_KEYS
        ],
        visible=layout_preset == "focus",
        on_select=lambda e: on_focus_sensor(e.control.value or "bmi270"),
    )

    layout_row = ft.Row(
        [
            ft.Text("Layout", size=11, color=TEXT_MUTED),
            segmented_chips(
                [("grid", "Grid"), ("stack", "Stack"), ("focus", "Focus")],
                layout_preset,
                on_layout,
                dense=True,
            ),
            focus_dd,
        ],
        spacing=8,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return ft.Column([layout_row, scene_row], spacing=8)
