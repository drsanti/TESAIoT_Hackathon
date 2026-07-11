"""Ring buffers and sparkline charts for live sensor plots (Flet 0.85+)."""

from __future__ import annotations

from collections import deque

import flet as ft

from ui.theme import BORDER, CARD, TEXT_MUTED

DEFAULT_CAPACITY = 120
DISPLAY_POINTS = 80

_SERIES_COLORS = (
    ft.Colors.CYAN_400,
    ft.Colors.TEAL_300,
    ft.Colors.AMBER_300,
    ft.Colors.ORANGE_300,
)


class RingBuffer:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._values: deque[float] = deque(maxlen=capacity)
        self.capacity = capacity

    def push(self, value: float | None) -> None:
        if value is None:
            return
        self._values.append(float(value))

    def clear(self) -> None:
        self._values.clear()

    def values(self) -> list[float]:
        return list(self._values)

    def __len__(self) -> int:
        return len(self._values)


class MultiSeriesBuffer:
    """Named series ring buffers for one chart."""

    def __init__(self, names: tuple[str, ...], capacity: int = DEFAULT_CAPACITY) -> None:
        self.names = names
        self._series = {n: RingBuffer(capacity) for n in names}

    def push(self, values: dict[str, float | None]) -> None:
        for name in self.names:
            self._series[name].push(values.get(name))

    def clear(self) -> None:
        for buf in self._series.values():
            buf.clear()

    def series_values(self) -> dict[str, list[float]]:
        return {name: buf.values() for name, buf in self._series.items()}


class SparklineRow(ft.Column):
    """One labeled series as a row of vertical ticks (no LineChart dependency)."""

    def __init__(
        self,
        label: str,
        *,
        color=ft.Colors.CYAN_400,
        y_min: float,
        y_max: float,
        point_count: int = DISPLAY_POINTS,
    ) -> None:
        self._y_min = y_min
        self._y_max = y_max
        self._ticks = [
            ft.Container(
                width=3,
                height=2,
                bgcolor=color,
                border_radius=2,
                alignment=ft.Alignment.BOTTOM_CENTER,
            )
            for _ in range(point_count)
        ]
        super().__init__(
            [
                ft.Text(label, size=10, color=TEXT_MUTED),
                ft.Container(
                    height=44,
                    content=ft.Row(
                        self._ticks,
                        spacing=1,
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
                ),
            ],
            spacing=2,
        )

    def set_values(self, values: list[float]) -> None:
        if not values:
            for tick in self._ticks:
                tick.height = 2
            return
        window = values[-len(self._ticks) :]
        span = self._y_max - self._y_min
        for i, tick in enumerate(self._ticks):
            if i >= len(window):
                tick.height = 2
                continue
            v = window[i]
            if span <= 0:
                tick.height = 2
            else:
                norm = max(0.0, min(1.0, (v - self._y_min) / span))
                tick.height = max(2, int(norm * 40))


class LineSeriesChart(ft.Container):
    """Sparkline panel — API kept for live_widgets; not ft.LineChart."""

    def __init__(
        self,
        *,
        title: str,
        y_min: float,
        y_max: float,
        height: float = 140,
        series_labels: tuple[str, ...] = ("S1", "S2", "S3"),
    ) -> None:
        self._y_min = y_min
        self._y_max = y_max
        self._rows = [
            SparklineRow(
                lab,
                color=_SERIES_COLORS[i % len(_SERIES_COLORS)],
                y_min=y_min,
                y_max=y_max,
            )
            for i, lab in enumerate(series_labels)
        ]
        super().__init__(
            content=ft.Column(
                [
                    ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                    *self._rows,
                ],
                spacing=6,
            ),
            bgcolor=CARD,
            border_radius=8,
            padding=8,
            height=height,
        )

    def set_series_data(self, series: dict[str, list[float]]) -> None:
        for row, key in zip(self._rows, series.keys(), strict=False):
            row.set_values(series.get(key, []))

    def set_y_range(self, y_min: float, y_max: float) -> None:
        self._y_min = y_min
        self._y_max = y_max
        for row in self._rows:
            row._y_min = y_min
            row._y_max = y_max
