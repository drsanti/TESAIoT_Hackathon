"""Visual tokens and small UI factories for ble-flet."""

from __future__ import annotations

import flet as ft

# Bitstream HMI-aligned dark palette
BG = "#08080C"
SURFACE = "#0E0E14"
CARD = "#12121A"
BORDER = "#38384A"
TEXT = "#E4E4E7"
TEXT_MUTED = "#71717A"
ACCENT = "#38BDF8"

SENSOR_STRIPE: dict[str, str] = {
    "bmi270": "#22D3EE",
    "bmm350": "#A78BFA",
    "sht40": "#FB923C",
    "dps368": "#4ADE80",
}

SIDEBAR_EXPANDED_W = 220
SIDEBAR_COLLAPSED_W = 56

ROUTE_LABELS: dict[str, str] = {
    "live": "Live",
    "connect": "Connect",
    "log": "Log",
    "settings": "Settings",
}

ROUTE_ICONS: dict[str, str] = {
    "live": ft.Icons.SENSORS,
    "connect": ft.Icons.BLUETOOTH,
    "log": ft.Icons.TERMINAL,
    "settings": ft.Icons.SETTINGS,
}


def card_shell(
    content: ft.Control,
    *,
    accent: str | None = None,
    padding: int = 16,
) -> ft.Container:
    border = ft.Border(
        left=ft.BorderSide(3, accent) if accent else ft.BorderSide(0, "transparent"),
        top=ft.BorderSide(1, BORDER),
        right=ft.BorderSide(1, BORDER),
        bottom=ft.BorderSide(1, BORDER),
    )
    return ft.Container(
        content=content,
        bgcolor=CARD,
        border=border,
        border_radius=12,
        padding=padding,
    )


def phase_ft_color(color_key: str) -> str:
    return {
        "green": ft.Colors.GREEN_300,
        "amber": ft.Colors.AMBER_300,
        "blue": ft.Colors.LIGHT_BLUE_400,
        "grey": ft.Colors.GREY_400,
    }.get(color_key, ft.Colors.GREY_400)


def segmented_chips(
    options: list[tuple[str, str]],
    selected: str,
    on_select,
    *,
    dense: bool = False,
) -> ft.Container:
    """Segmented control — muted track, accent active chip."""
    controls: list[ft.Control] = []
    for key, label in options:
        active = key == selected
        controls.append(
            ft.Container(
                content=ft.Text(
                    label,
                    size=11 if dense else 12,
                    weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
                    color=TEXT if active else TEXT_MUTED,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=7 if dense else 8),
                bgcolor="#152033" if active else "transparent",
                border=ft.Border.all(1, ACCENT if active else "transparent"),
                border_radius=8,
                on_click=lambda e, k=key: on_select(k),
                ink=True,
            )
        )
    return ft.Container(
        content=ft.Row(controls, spacing=4, wrap=False),
        padding=4,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=10,
    )


def plot_mode_toggle(
    selected: str,
    on_select,
) -> ft.Row:
    return segmented_chips(
        [("bars", "Bars"), ("lines", "Lines")],
        selected,
        on_select,
        dense=True,
    )
