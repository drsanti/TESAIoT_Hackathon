"""Connect / manual BLE tools page."""

from __future__ import annotations

import flet as ft

from ui.theme import BORDER, CARD, TEXT_MUTED


class ConnectPage:
    def __init__(
        self,
        *,
        device_dropdown: ft.Dropdown,
        scan_btn: ft.Control,
        connect_btn: ft.Control,
        park_btn: ft.Control,
        ping_btn: ft.Control,
        link_btn: ft.Control,
        snapshot_btn: ft.Control,
        resume_btn: ft.Control,
        policy_text: ft.Text,
        link_text: ft.Text,
        status_text: ft.Text,
        sensor_tiles: list[ft.Control],
    ) -> None:
        self.device_dropdown = device_dropdown
        self.connect_btn = connect_btn
        self.scan_btn = scan_btn
        self.park_btn = park_btn
        self.ping_btn = ping_btn
        self.link_btn = link_btn
        self.snapshot_btn = snapshot_btn
        self.resume_btn = resume_btn
        self.policy_text = policy_text
        self.link_text = link_text
        self.status_text = status_text
        self._sensor_tiles = sensor_tiles

    def build(self) -> ft.Control:
        device_card = ft.Container(
            bgcolor=CARD,
            border=ft.Border.all(1, BORDER),
            border_radius=10,
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Device", size=12, weight=ft.FontWeight.W_600),
                    self.device_dropdown,
                    ft.Row(
                        [self.scan_btn, self.connect_btn, self.park_btn, self.resume_btn],
                        wrap=True,
                        spacing=8,
                    ),
                    self.status_text,
                ],
                spacing=10,
            ),
        )
        link_card = ft.Container(
            bgcolor=CARD,
            border=ft.Border.all(1, BORDER),
            border_radius=10,
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Link health", size=12, weight=ft.FontWeight.W_600),
                    self.policy_text,
                    self.link_text,
                    ft.Row(
                        [self.ping_btn, self.link_btn, self.snapshot_btn],
                        wrap=True,
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
        )
        debug_grid = ft.ResponsiveRow(
            [ft.Container(tile, col={"xs": 12, "md": 6}) for tile in self._sensor_tiles],
            spacing=10,
            run_spacing=10,
        )
        return ft.Column(
            [
                ft.Text(
                    "Scan, connect, and inspect link health. Auto handles demos on the Live page.",
                    size=12,
                    color=TEXT_MUTED,
                ),
                device_card,
                link_card,
                ft.Text("Debug rows", size=12, weight=ft.FontWeight.W_600),
                debug_grid,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
