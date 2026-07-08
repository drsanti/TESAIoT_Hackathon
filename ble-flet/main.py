#!/usr/bin/env python3
"""TESAIoT hackathon — desktop BLE dashboard (Flet + bleak)."""

from __future__ import annotations

import flet as ft

from ui.app import BleDashboardApp


async def main(page: ft.Page) -> None:
    page.title = "TESAIoT BLE"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 1100
    page.window.height = 800

    app = BleDashboardApp(page)
    page.add(app.build())
    app.start()


if __name__ == "__main__":
    ft.run(main)
