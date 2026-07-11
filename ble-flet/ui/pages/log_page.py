"""Full-height log viewer page."""

from __future__ import annotations

import flet as ft

from ui.theme import BORDER, TEXT_MUTED


class LogPage:
    def __init__(
        self,
        *,
        log_list: ft.ListView,
        log_meta: ft.Text,
        log_copy_status: ft.Text,
        copy_log_btn: ft.Control,
        copy_snapshot_btn: ft.Control,
        clear_btn: ft.Control,
    ) -> None:
        self.log_list = log_list
        self.log_meta = log_meta
        self.log_copy_status = log_copy_status
        self._copy_log_btn = copy_log_btn
        self._copy_snapshot_btn = copy_snapshot_btn
        self._clear_btn = clear_btn

    def build(self) -> ft.Control:
        toolbar = ft.Row(
            [
                self._copy_log_btn,
                self._copy_snapshot_btn,
                self._clear_btn,
                self.log_meta,
                self.log_copy_status,
            ],
            wrap=True,
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Column(
            [
                ft.Text(
                    "Timestamped diagnostics — copy log or snapshot for chat analysis.",
                    size=12,
                    color=TEXT_MUTED,
                ),
                toolbar,
                ft.Container(
                    content=self.log_list,
                    expand=True,
                    border=ft.Border.all(1, BORDER),
                    border_radius=8,
                    padding=8,
                ),
            ],
            spacing=8,
            expand=True,
        )
