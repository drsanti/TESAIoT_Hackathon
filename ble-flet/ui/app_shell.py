"""App shell — sidebar + routed main content."""

from __future__ import annotations

import flet as ft

from ui.theme import BG, BORDER, TEXT, TEXT_MUTED


class AppShell(ft.Container):
    def __init__(
        self,
        *,
        sidebar: ft.Control,
        top_bar: ft.Control,
        content: ft.Control,
    ) -> None:
        self.sidebar = sidebar
        self.top_bar = top_bar
        self.main_content = ft.Container(content=content, expand=True, padding=20)
        self._main_column = ft.Column(
            [
                self.top_bar,
                self.main_content,
            ],
            expand=True,
            spacing=0,
        )

        super().__init__(
            expand=True,
            bgcolor=BG,
            content=ft.Row(
                [
                    sidebar,
                    ft.Container(
                        content=self._main_column,
                        expand=True,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        )

    def set_page_content(self, content: ft.Control) -> None:
        self.main_content.content = content

    def set_top_bar(self, top_bar: ft.Control) -> None:
        self.top_bar = top_bar
        self._main_column.controls[0] = top_bar


def build_top_bar(
    *,
    route_title: str,
    subtitle: str | None = None,
    trailing: ft.Control | None = None,
) -> ft.Container:
    title_col: list[ft.Control] = [
        ft.Text(route_title, size=20, weight=ft.FontWeight.W_600, color=TEXT),
    ]
    if subtitle:
        title_col.append(ft.Text(subtitle, size=12, color=TEXT_MUTED))

    row_controls: list[ft.Control] = [
        ft.Column(title_col, spacing=2),
    ]
    if trailing is not None:
        row_controls.append(ft.Container(expand=True))
        row_controls.append(trailing)
    return ft.Container(
        content=ft.Row(
            row_controls,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
    )
