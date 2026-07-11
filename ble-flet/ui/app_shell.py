"""App shell — sidebar + routed main content."""

from __future__ import annotations

import flet as ft

from ui.theme import BG, TEXT, TEXT_MUTED


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
        self.main_content = ft.Container(content=content, expand=True, padding=16)

        super().__init__(
            expand=True,
            bgcolor=BG,
            content=ft.Row(
                [
                    sidebar,
                    ft.Container(
                        content=ft.Column(
                            [
                                top_bar,
                                self.main_content,
                            ],
                            expand=True,
                            spacing=0,
                        ),
                        expand=True,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        )

    def set_page_content(self, content: ft.Control) -> None:
        self.main_content.content = content


def build_top_bar(
    *,
    route_title: str,
    trailing: ft.Control | None = None,
) -> ft.Container:
    row_controls: list[ft.Control] = [
        ft.Text(route_title, size=18, weight=ft.FontWeight.W_600, color=TEXT),
    ]
    if trailing is not None:
        row_controls.append(ft.Container(expand=True))
        row_controls.append(trailing)
    return ft.Container(
        content=ft.Row(row_controls, alignment=ft.MainAxisAlignment.START),
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE))),
    )
