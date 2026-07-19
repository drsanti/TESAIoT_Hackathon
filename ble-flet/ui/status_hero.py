"""Status hero — phase, device, policy summary."""

from __future__ import annotations

import flet as ft

from ui.theme import BORDER, CARD, TEXT, TEXT_MUTED, phase_ft_color


class StatusHero(ft.Container):
    def __init__(
        self,
        *,
        on_stream_on,
    ) -> None:
        self._on_stream_on = on_stream_on
        self.chip = ft.Text("Disconnected", size=15, weight=ft.FontWeight.W_700)
        self.detail = ft.Text("Waiting for device…", size=12, color=TEXT_MUTED)
        self.meta = ft.Text("policy —", size=11, color=TEXT_MUTED)
        self.stream_btn = ft.FilledButton(
            "Stream on",
            icon=ft.Icons.PLAY_ARROW,
            visible=False,
            on_click=lambda e: self._on_stream_on(e),
        )

        super().__init__(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            self.chip,
                            self.detail,
                            self.meta,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    self.stream_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=CARD,
            border=ft.Border.all(1, BORDER),
            border_radius=10,
            padding=16,
        )

    def update(
        self,
        *,
        chip_label: str,
        chip_color_key: str,
        detail: str,
        meta: str,
        show_stream_on: bool,
    ) -> None:
        self.chip.value = chip_label
        self.chip.color = phase_ft_color(chip_color_key)
        self.detail.value = detail
        self.detail.color = TEXT
        self.meta.value = meta
        self.stream_btn.visible = show_stream_on
