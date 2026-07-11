"""Collapsible left navigation rail."""

from __future__ import annotations

import flet as ft

from ui.theme import (
    ACCENT,
    BG,
    BORDER,
    ROUTE_ICONS,
    ROUTE_LABELS,
    SIDEBAR_COLLAPSED_W,
    SIDEBAR_EXPANDED_W,
    TEXT,
    TEXT_MUTED,
    phase_ft_color,
)


class SidebarNav(ft.Container):
    def __init__(
        self,
        *,
        collapsed: bool,
        active_route: str,
        phase_color_key: str,
        device_name: str,
        device_address: str | None,
        on_nav,
        on_toggle,
    ) -> None:
        self._collapsed = collapsed
        self._active_route = active_route
        self._phase_color_key = phase_color_key
        self._device_name = device_name
        self._device_address = device_address
        self._on_nav = on_nav
        self._on_toggle = on_toggle

        self._nav_column = ft.Column(spacing=4)
        self._footer = ft.Container()
        self._brand = ft.Text("TESAIoT BLE", size=14, weight=ft.FontWeight.W_700, color=ACCENT)

        super().__init__(
            width=SIDEBAR_COLLAPSED_W if collapsed else SIDEBAR_EXPANDED_W,
            bgcolor=BG,
            border=ft.Border(right=ft.BorderSide(1, BORDER)),
            padding=ft.Padding.only(left=8, right=8, top=12, bottom=8),
            content=ft.Column(
                [
                    self._header(),
                    ft.Container(height=8),
                    self._nav_column,
                    ft.Container(expand=True),
                    self._footer,
                    self._toggle_btn(),
                ],
                expand=True,
            ),
        )
        self._rebuild()

    def _header(self) -> ft.Control:
        if self._collapsed:
            return ft.Container(
                content=ft.Icon(ft.Icons.BLUETOOTH_CONNECTED, color=ACCENT, size=22),
                alignment=ft.Alignment.CENTER,
                tooltip="TESAIoT BLE",
            )
        return self._brand

    def _toggle_btn(self) -> ft.Control:
        icon = ft.Icons.CHEVRON_RIGHT if self._collapsed else ft.Icons.CHEVRON_LEFT
        label = "Expand" if self._collapsed else "Collapse"
        if self._collapsed:
            return ft.IconButton(
                icon=icon,
                tooltip=label,
                on_click=lambda e: self._on_toggle(),
            )
        return ft.TextButton(
            content="Collapse",
            icon=icon,
            on_click=lambda e: self._on_toggle(),
        )

    def _nav_item(self, route: str) -> ft.Control:
        active = route == self._active_route
        icon = ROUTE_ICONS.get(route, ft.Icons.CIRCLE)
        color = ACCENT if active else TEXT_MUTED
        if self._collapsed:
            return ft.Container(
                content=ft.Icon(icon, color=color, size=22),
                padding=10,
                border_radius=8,
                bgcolor="#1A1A24" if active else None,
                border=ft.Border(
                    left=ft.BorderSide(3, ACCENT if active else "transparent"),
                ),
                alignment=ft.Alignment.CENTER,
                tooltip=ROUTE_LABELS.get(route, route),
                on_click=lambda e, r=route: self._on_nav(r),
                ink=True,
            )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=color, size=18),
                    ft.Text(
                        ROUTE_LABELS.get(route, route),
                        size=13,
                        weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL,
                        color=TEXT if active else TEXT_MUTED,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=10),
            border_radius=8,
            bgcolor="#1A1A24" if active else None,
            border=ft.Border(
                left=ft.BorderSide(3, ACCENT if active else "transparent"),
            ),
            on_click=lambda e, r=route: self._on_nav(r),
            ink=True,
        )

    def _rebuild_footer(self) -> None:
        dot_color = phase_ft_color(self._phase_color_key)
        if self._collapsed:
            self._footer.content = ft.Container(
                content=ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, color=dot_color, size=14),
                alignment=ft.Alignment.CENTER,
                tooltip=self._device_name or "No device",
            )
            return
        addr = self._device_address or "-"
        if len(addr) > 17:
            addr = addr[:8] + "…" + addr[-8:]
        self._footer.content = ft.Column(
            [
                ft.Divider(height=1, color=BORDER),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, color=dot_color, size=12),
                        ft.Column(
                            [
                                ft.Text(
                                    self._device_name or "No device",
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    color=TEXT,
                                ),
                                ft.Text(addr, size=10, color=TEXT_MUTED),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ],
                    spacing=6,
                ),
            ],
            spacing=8,
        )

    def _rebuild(self) -> None:
        self.width = SIDEBAR_COLLAPSED_W if self._collapsed else SIDEBAR_EXPANDED_W
        self.content.controls[0] = self._header()
        self._nav_column.controls = [
            self._nav_item("live"),
            self._nav_item("connect"),
            self._nav_item("log"),
            self._nav_item("settings"),
        ]
        self._rebuild_footer()
        self.content.controls[-1] = self._toggle_btn()

    def update_state(
        self,
        *,
        collapsed: bool | None = None,
        active_route: str | None = None,
        phase_color_key: str | None = None,
        device_name: str | None = None,
        device_address: str | None = None,
    ) -> None:
        if collapsed is not None:
            self._collapsed = collapsed
        if active_route is not None:
            self._active_route = active_route
        if phase_color_key is not None:
            self._phase_color_key = phase_color_key
        if device_name is not None:
            self._device_name = device_name
        if device_address is not None:
            self._device_address = device_address
        self._rebuild()
