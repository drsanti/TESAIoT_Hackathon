"""Live sensors page — hero, layout, scenes, grid."""

from __future__ import annotations

import flet as ft

from ui.live_grid import LiveGridHost, layout_toolbar_row
from ui.status_hero import StatusHero
from ui.theme import TEXT_MUTED


class LivePage:
    def __init__(
        self,
        *,
        hero: StatusHero,
        grid_host: LiveGridHost,
        layout_preset: str,
        focus_sensor: str,
        on_layout,
        on_focus_sensor,
        scene_row: ft.Control,
        footer_row: ft.Control,
        hint: ft.Text,
    ) -> None:
        self.hero = hero
        self.grid_host = grid_host
        self._hint = hint
        self._toolbar = layout_toolbar_row(
            layout_preset=layout_preset,
            focus_sensor=focus_sensor,
            on_layout=on_layout,
            on_focus_sensor=on_focus_sensor,
            scene_row=scene_row,
        )
        self._footer = footer_row

    def rebuild_toolbar(
        self,
        *,
        layout_preset: str,
        focus_sensor: str,
        on_layout,
        on_focus_sensor,
        scene_row: ft.Control,
    ) -> None:
        self._toolbar = layout_toolbar_row(
            layout_preset=layout_preset,
            focus_sensor=focus_sensor,
            on_layout=on_layout,
            on_focus_sensor=on_focus_sensor,
            scene_row=scene_row,
        )

    def build(self) -> ft.Control:
        return ft.Column(
            [
                self.hero,
                self._hint,
                self._toolbar,
                self.grid_host,
                self._footer,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def update_hint(self, text: str) -> None:
        self._hint.value = text
