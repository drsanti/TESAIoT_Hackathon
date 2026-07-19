#!/usr/bin/env python3
"""TESAIoT hackathon — desktop BLE dashboard (Flet + bleak)."""

from __future__ import annotations

import flet as ft

from ui.app import BleDashboardApp
from ui.theme import BG


async def main(page: ft.Page) -> None:
    page.title = "TESAIoT BLE"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    page.window.width = 1200
    page.window.height = 820
    page.window.min_width = 900

    app = BleDashboardApp(page)
    page.add(app.build())
    app.start()


if __name__ == "__main__":
    ft.run(main)
