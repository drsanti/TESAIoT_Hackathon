"""Live sensor visualization widgets (bars, lines, big numbers)."""

from __future__ import annotations

import math
from typing import Callable

import flet as ft

from bs2.decode import SENSOR_LABELS
from ui.charts import LineSeriesChart, MultiSeriesBuffer
from ui.theme import ACCENT, BORDER, CARD, SENSOR_STRIPE, SURFACE, TEXT, TEXT_MUTED, plot_mode_toggle


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _axis_level(value: float, span: float) -> float:
    if span <= 0:
        return 0.0
    return _clamp01(abs(value) / span)


def _section_label(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=10,
        weight=ft.FontWeight.W_600,
        color=TEXT_MUTED,
    )


def _soft_panel(content: ft.Control, *, expand: bool = True) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        expand=expand,
    )


class AxisBars(ft.Column):
    def __init__(self, title: str, labels: tuple[str, str, str], *, span: float) -> None:
        bars: list[ft.ProgressBar] = []
        vals: list[ft.Text] = []
        rows: list[ft.Control] = [_section_label(title)]
        bar_colors = (ft.Colors.CYAN_400, ft.Colors.TEAL_300, ft.Colors.AMBER_300)
        for i, lab in enumerate(labels):
            val = ft.Text(f"{lab}  —", size=12, color=TEXT_MUTED)
            bar = ft.ProgressBar(
                value=0,
                bar_height=6,
                color=bar_colors[i],
                bgcolor="#1A1A24",
            )
            bars.append(bar)
            vals.append(val)
            rows.append(ft.Column([val, bar], spacing=2))
        super().__init__(rows, spacing=5, expand=True)
        self._span = span
        self._labels = labels
        self._bars = bars
        self._vals = vals

    def set_xyz(self, x: float | None, y: float | None, z: float | None) -> None:
        for i, raw in enumerate((x, y, z)):
            lab = self._labels[i]
            if raw is None:
                self._bars[i].value = 0
                self._vals[i].value = f"{lab}  —"
                self._vals[i].color = TEXT_MUTED
            else:
                self._bars[i].value = _axis_level(raw, self._span)
                self._vals[i].value = f"{lab}  {raw:+.2f}"
                self._vals[i].color = TEXT


class ScalarBar(ft.Column):
    def __init__(
        self,
        title: str,
        *,
        lo: float,
        hi: float,
        unit: str,
        color=ft.Colors.CYAN_400,
    ) -> None:
        big = ft.Text("—", size=26, weight=ft.FontWeight.W_600, color=TEXT)
        bar = ft.ProgressBar(value=0, bar_height=8, color=color, bgcolor="#1A1A24")
        super().__init__(
            [
                _section_label(title),
                big,
                bar,
            ],
            spacing=4,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
        self._lo = lo
        self._hi = hi
        self._unit = unit
        self._big = big
        self._bar = bar

    def set_value(self, value: float | None) -> None:
        if value is None or not math.isfinite(value):
            self._big.value = "—"
            self._bar.value = 0
            return
        self._big.value = f"{value:.1f} {self._unit}"
        span = self._hi - self._lo
        self._bar.value = _clamp01((value - self._lo) / span) if span else 0


class _OrientTile(ft.Container):
    def __init__(self, label: str, accent: str) -> None:
        self._value = ft.Text("—", size=28, weight=ft.FontWeight.W_600, color=TEXT)
        self._unit = ft.Text("deg", size=10, color=TEXT_MUTED)
        self._bar = ft.ProgressBar(
            value=0.5,
            bar_height=4,
            color=accent,
            bgcolor="#1A1A24",
        )
        super().__init__(
            content=ft.Column(
                [
                    ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                    ft.Row(
                        [self._value, self._unit],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    self._bar,
                ],
                spacing=4,
                tight=True,
            ),
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True,
        )
        self._accent = accent

    def set_deg(self, deg: float | None, *, kind: str) -> None:
        if deg is None or not math.isfinite(deg):
            self._value.value = "—"
            self._value.color = TEXT_MUTED
            self._bar.value = 0.5
            return
        self._value.color = TEXT
        if kind == "yaw":
            wrapped = deg % 360.0
            self._value.value = f"{wrapped:.0f}"
            self._bar.value = _clamp01(wrapped / 360.0)
        else:
            self._value.value = f"{deg:+.0f}"
            self._bar.value = _clamp01((deg + 90.0) / 180.0)


class OrientationPanel(ft.Column):
    """Yaw / pitch / roll as three equal tiles."""

    def __init__(self) -> None:
        self._yaw = _OrientTile("YAW", ACCENT)
        self._pitch = _OrientTile("PITCH", ft.Colors.TEAL_300)
        self._roll = _OrientTile("ROLL", ft.Colors.AMBER_300)
        self._hint = ft.Text("", size=10, color=TEXT_MUTED, visible=False)
        super().__init__(
            [
                _section_label("ORIENTATION"),
                ft.ResponsiveRow(
                    [
                        ft.Container(self._yaw, col={"xs": 12, "sm": 4}),
                        ft.Container(self._pitch, col={"xs": 12, "sm": 4}),
                        ft.Container(self._roll, col={"xs": 12, "sm": 4}),
                    ],
                    spacing=8,
                    run_spacing=8,
                ),
                self._hint,
            ],
            spacing=8,
        )

    def set_fields(self, fields: dict[str, float]) -> None:
        def deg(rad_key: str) -> float | None:
            if rad_key not in fields:
                return None
            return fields[rad_key] * (180.0 / math.pi)

        h = deg("headingRad")
        p = deg("pitchRad")
        r = deg("rollRad")
        self._yaw.set_deg(h, kind="yaw")
        self._pitch.set_deg(p, kind="pitch")
        self._roll.set_deg(r, kind="roll")
        missing = h is None and p is None and r is None
        self._hint.visible = missing
        self._hint.value = "No Euler on wire — use fusion/hybrid with mask 0x1f" if missing else ""


class QuaternionPanel(ft.Column):
    """Four equal quaternion chips."""

    def __init__(self) -> None:
        self._chips: dict[str, ft.Text] = {}
        chip_row: list[ft.Control] = []
        for key, label in (("w", "W"), ("x", "X"), ("y", "Y"), ("z", "Z")):
            val = ft.Text("—", size=18, weight=ft.FontWeight.W_600, color=TEXT_MUTED)
            self._chips[key] = val
            chip_row.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                            val,
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    bgcolor=SURFACE,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=10),
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                )
            )
        self._hint = ft.Text("", size=10, color=TEXT_MUTED, visible=False)
        super().__init__(
            [
                _section_label("QUATERNION"),
                ft.Row(chip_row, spacing=8, expand=True),
                self._hint,
            ],
            spacing=8,
        )

    def set_fields(self, fields: dict[str, float]) -> None:
        qw = fields.get("quatW")
        qx = fields.get("quatX")
        qy = fields.get("quatY")
        qz = fields.get("quatZ")
        mapping = {"w": qw, "x": qx, "y": qy, "z": qz}
        any_present = False
        for key, raw in mapping.items():
            txt = self._chips[key]
            if raw is None or not math.isfinite(raw):
                txt.value = "—"
                txt.color = TEXT_MUTED
            else:
                any_present = True
                txt.value = f"{raw:.3f}"
                txt.color = TEXT
        self._hint.visible = not any_present
        self._hint.value = "No quaternion on wire — enable fusion bits in SENSOR_CFG" if not any_present else ""


class MetaLine(ft.Row):
    def __init__(self) -> None:
        self._temp = ft.Text("Temp  —", size=11, color=TEXT_MUTED)
        super().__init__([self._temp], spacing=12)

    def set_temp(self, value: float | None) -> None:
        if value is None or not math.isfinite(value):
            self._temp.value = "Temp  —"
        else:
            self._temp.value = f"Temp  {value:.1f} °C"
            self._temp.color = TEXT


class EulerTracks(OrientationPanel):
    """Backward-compatible alias used by app debug paths. """

    pass


def _build_bars_body(sensor_key: str) -> tuple[ft.Column, dict]:
    refs: dict = {}
    body = ft.Column(spacing=12)
    if sensor_key == "bmi270":
        orient = OrientationPanel()
        quat = QuaternionPanel()
        accel = AxisBars("ACCEL (g)", ("X", "Y", "Z"), span=2.0)
        gyro = AxisBars("GYRO", ("X", "Y", "Z"), span=250.0)
        meta = MetaLine()
        refs = {
            "orient": orient,
            "quat": quat,
            "euler": orient,
            "accel": accel,
            "gyro": gyro,
            "meta": meta,
        }
        body.controls = [
            orient,
            quat,
            _section_label("MOTION"),
            ft.ResponsiveRow(
                [
                    ft.Container(_soft_panel(accel), col={"xs": 12, "md": 6}),
                    ft.Container(_soft_panel(gyro), col={"xs": 12, "md": 6}),
                ],
                spacing=8,
                run_spacing=8,
            ),
            meta,
        ]
    elif sensor_key == "bmm350":
        mag = AxisBars("Mag (uT)", ("X", "Y", "Z"), span=80.0)
        temp = ScalarBar("Temp", lo=0, hi=50, unit="C", color=ft.Colors.ORANGE_300)
        refs = {"mag": mag, "temp": temp}
        body.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(mag, col={"xs": 12, "md": 8}),
                    ft.Container(temp, col={"xs": 12, "md": 4}),
                ],
                spacing=8,
            ),
        ]
    elif sensor_key == "sht40":
        temp = ScalarBar("Temp", lo=-10, hi=60, unit="C", color=ft.Colors.ORANGE_400)
        rh = ScalarBar("Humidity", lo=0, hi=100, unit="%", color=ft.Colors.LIGHT_BLUE_400)
        refs = {"temp": temp, "rh": rh}
        body.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(temp, col={"xs": 12, "md": 6}),
                    ft.Container(rh, col={"xs": 12, "md": 6}),
                ],
                spacing=8,
            ),
        ]
    else:
        press = ScalarBar("Pressure", lo=980, hi=1040, unit="hPa", color=ft.Colors.GREEN_400)
        temp = ScalarBar("Temp", lo=0, hi=50, unit="C", color=ft.Colors.ORANGE_300)
        refs = {"press": press, "temp": temp}
        body.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(press, col={"xs": 12, "md": 7}),
                    ft.Container(temp, col={"xs": 12, "md": 5}),
                ],
                spacing=8,
            ),
        ]
    return body, refs


def _build_lines_body(sensor_key: str) -> tuple[ft.Column, dict]:
    refs: dict = {}
    body = ft.Column(spacing=10, expand=True)
    if sensor_key == "bmi270":
        accel_buf = MultiSeriesBuffer(("X", "Y", "Z"))
        gyro_buf = MultiSeriesBuffer(("X", "Y", "Z"))
        euler_buf = MultiSeriesBuffer(("yaw", "pitch", "roll"))
        quat = QuaternionPanel()
        euler_chart = LineSeriesChart(
            title="Orientation (deg)",
            y_min=-180,
            y_max=360,
            height=110,
            series_labels=("yaw", "pitch", "roll"),
        )
        accel_chart = LineSeriesChart(
            title="Accel (g)",
            y_min=-2,
            y_max=2,
            height=100,
            series_labels=("X", "Y", "Z"),
        )
        gyro_chart = LineSeriesChart(
            title="Gyro",
            y_min=-250,
            y_max=250,
            height=100,
            series_labels=("X", "Y", "Z"),
        )
        refs = {
            "accel_buf": accel_buf,
            "gyro_buf": gyro_buf,
            "euler_buf": euler_buf,
            "accel_chart": accel_chart,
            "gyro_chart": gyro_chart,
            "euler_chart": euler_chart,
            "quat": quat,
        }
        body.controls = [
            _section_label("ORIENTATION"),
            euler_chart,
            quat,
            _section_label("MOTION"),
            ft.ResponsiveRow(
                [
                    ft.Container(accel_chart, col={"xs": 12, "md": 6}),
                    ft.Container(gyro_chart, col={"xs": 12, "md": 6}),
                ],
                spacing=8,
            ),
        ]
    elif sensor_key == "bmm350":
        mag_buf = MultiSeriesBuffer(("X", "Y", "Z"))
        temp_buf = MultiSeriesBuffer(("temp",))
        mag_chart = LineSeriesChart(
            title="Mag (uT)",
            y_min=-80,
            y_max=80,
            height=130,
            series_labels=("X", "Y", "Z"),
        )
        temp_chart = LineSeriesChart(
            title="Temp (C)",
            y_min=0,
            y_max=50,
            height=100,
            series_labels=("temp",),
        )
        refs = {"mag_buf": mag_buf, "temp_buf": temp_buf, "mag_chart": mag_chart, "temp_chart": temp_chart}
        body.controls = [mag_chart, temp_chart]
    elif sensor_key == "sht40":
        buf = MultiSeriesBuffer(("temp", "rh"))
        chart = LineSeriesChart(
            title="Temp / RH",
            y_min=0,
            y_max=100,
            height=140,
            series_labels=("temp", "rh"),
        )
        refs = {"buf": buf, "chart": chart}
        body.controls = [chart]
    else:
        buf = MultiSeriesBuffer(("pressure", "temp"))
        chart = LineSeriesChart(
            title="Pressure / Temp",
            y_min=0,
            y_max=1100,
            height=140,
            series_labels=("pressure", "temp"),
        )
        refs = {"buf": buf, "chart": chart}
        body.controls = [chart]
    return body, refs


class SensorLiveCard(ft.Container):
    def __init__(
        self,
        sensor_key: str,
        *,
        plot_mode: str = "bars",
        on_plot_mode_change: Callable[[str, str], None] | None = None,
    ) -> None:
        self.sensor_key = sensor_key
        self._plot_mode = plot_mode
        self._on_plot_mode_change = on_plot_mode_change
        self._compact = False

        stripe = SENSOR_STRIPE.get(sensor_key, "#71717A")
        self._title_text = ft.Text(
            SENSOR_LABELS.get(sensor_key, sensor_key),
            weight=ft.FontWeight.W_600,
            size=14,
            color=TEXT,
        )
        self._mode_chip = ft.Container(
            content=ft.Text("—", size=10, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER),
            border_radius=999,
        )
        self._badge_text = ft.Text("waiting…", size=11, color=TEXT_MUTED)
        self._stats_text = ft.Text("—", size=11, color=ACCENT)
        self._plot_toggle_host = ft.Container()

        self._bars_body, self._bars_refs = _build_bars_body(sensor_key)
        self._lines_body: ft.Column | None = None
        self._lines_refs: dict = {}
        self._body_host = ft.Container(expand=True)

        super().__init__(
            content=ft.Column(
                [
                    self._header_row(),
                    ft.Row(
                        [self._badge_text, ft.Container(expand=True), self._stats_text],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=1, bgcolor=BORDER),
                    self._body_host,
                ],
                spacing=8,
            ),
            bgcolor=CARD,
            border=ft.Border(
                left=ft.BorderSide(3, stripe),
                top=ft.BorderSide(1, BORDER),
                right=ft.BorderSide(1, BORDER),
                bottom=ft.BorderSide(1, BORDER),
            ),
            border_radius=12,
            padding=16,
        )
        self._sync_body()

    @property
    def plot_mode(self) -> str:
        return self._plot_mode

    def _header_row(self) -> ft.Row:
        self._plot_toggle_host.content = plot_mode_toggle(
            self._plot_mode,
            self._select_plot_mode,
        )
        return ft.Row(
            [
                self._title_text,
                self._mode_chip,
                ft.Container(expand=True),
                self._plot_toggle_host,
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

    def _select_plot_mode(self, mode: str) -> None:
        if mode == self._plot_mode:
            return
        self._plot_mode = mode
        self._plot_toggle_host.content = plot_mode_toggle(mode, self._select_plot_mode)
        self._sync_body()
        if self._on_plot_mode_change:
            self._on_plot_mode_change(self.sensor_key, mode)

    def _ensure_lines_body(self) -> None:
        if self._lines_body is None:
            self._lines_body, self._lines_refs = _build_lines_body(self.sensor_key)

    def _sync_body(self) -> None:
        if self._plot_mode == "lines":
            self._ensure_lines_body()
            self._body_host.content = self._lines_body
        else:
            self._body_host.content = self._bars_body

    def set_plot_mode(self, mode: str) -> None:
        if mode not in ("bars", "lines"):
            return
        self._plot_mode = mode
        self._plot_toggle_host.content = plot_mode_toggle(mode, self._select_plot_mode)
        self._sync_body()

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self._title_text.size = 13 if compact else 14
        self._stats_text.visible = not compact
        self._badge_text.visible = not compact
        self._mode_chip.visible = not compact

    def set_stats(self, line: str, *, ok: bool | None) -> None:
        self._stats_text.value = line
        if ok is True:
            self._stats_text.color = ft.Colors.GREEN_300
        elif ok is False:
            self._stats_text.color = ft.Colors.ORANGE_300
        else:
            self._stats_text.color = ACCENT

    def set_badge(self, text: str) -> None:
        self._badge_text.value = text
        # Promote stream mode into the header chip when present (e.g. "fusion · 15.2 Hz").
        lower = text.lower()
        mode = "—"
        for token in ("fusion", "hybrid", "raw"):
            if token in lower:
                mode = token
                break
        chip_text = self._mode_chip.content
        if isinstance(chip_text, ft.Text):
            chip_text.value = mode
            if mode == "fusion":
                chip_text.color = ACCENT
            elif mode == "hybrid":
                chip_text.color = ft.Colors.TEAL_300
            elif mode == "raw":
                chip_text.color = TEXT_MUTED
            else:
                chip_text.color = TEXT_MUTED

    def refresh_charts(self) -> None:
        key = self.sensor_key
        if self._plot_mode != "lines":
            return
        self._ensure_lines_body()
        if key == "bmi270":
            self._lines_refs["accel_chart"].set_series_data(self._lines_refs["accel_buf"].series_values())
            self._lines_refs["gyro_chart"].set_series_data(self._lines_refs["gyro_buf"].series_values())
            self._lines_refs["euler_chart"].set_series_data(self._lines_refs["euler_buf"].series_values())
        elif key == "bmm350":
            self._lines_refs["mag_chart"].set_series_data(self._lines_refs["mag_buf"].series_values())
            self._lines_refs["temp_chart"].set_series_data(self._lines_refs["temp_buf"].series_values())
        elif key == "sht40":
            self._lines_refs["chart"].set_series_data(self._lines_refs["buf"].series_values())
        else:
            self._lines_refs["chart"].set_series_data(self._lines_refs["buf"].series_values())

    def apply_sample(self, sample: dict) -> None:
        fields: dict[str, float] = sample.get("fields") or {}
        if self._plot_mode == "lines":
            self._apply_lines(fields)
            return
        self._apply_bars(fields)

    def _apply_bars(self, fields: dict[str, float]) -> None:
        key = self.sensor_key
        refs = self._bars_refs
        if key == "bmi270":
            refs["orient"].set_fields(fields)
            refs["quat"].set_fields(fields)
            refs["accel"].set_xyz(fields.get("accelX"), fields.get("accelY"), fields.get("accelZ"))
            refs["gyro"].set_xyz(fields.get("gyroX"), fields.get("gyroY"), fields.get("gyroZ"))
            refs["meta"].set_temp(fields.get("temperatureC"))
        elif key == "bmm350":
            refs["mag"].set_xyz(fields.get("magX"), fields.get("magY"), fields.get("magZ"))
            refs["temp"].set_value(fields.get("temperatureC"))
        elif key == "sht40":
            refs["temp"].set_value(fields.get("temperatureC"))
            refs["rh"].set_value(fields.get("humidityPct"))
        else:
            refs["press"].set_value(fields.get("pressureHpa") or fields.get("pressurePa"))
            refs["temp"].set_value(fields.get("temperatureC"))

    def _apply_lines(self, fields: dict[str, float]) -> None:
        self._ensure_lines_body()
        key = self.sensor_key
        refs = self._lines_refs
        if key == "bmi270":
            refs["quat"].set_fields(fields)
            refs["accel_buf"].push(
                {"X": fields.get("accelX"), "Y": fields.get("accelY"), "Z": fields.get("accelZ")}
            )
            refs["gyro_buf"].push(
                {"X": fields.get("gyroX"), "Y": fields.get("gyroY"), "Z": fields.get("gyroZ")}
            )
            h = fields.get("headingRad")
            p = fields.get("pitchRad")
            r = fields.get("rollRad")
            refs["euler_buf"].push(
                {
                    "yaw": (h * 180 / math.pi) if h is not None else None,
                    "pitch": (p * 180 / math.pi) if p is not None else None,
                    "roll": (r * 180 / math.pi) if r is not None else None,
                }
            )
        elif key == "bmm350":
            refs["mag_buf"].push(
                {"X": fields.get("magX"), "Y": fields.get("magY"), "Z": fields.get("magZ")}
            )
            refs["temp_buf"].push({"temp": fields.get("temperatureC")})
        elif key == "sht40":
            refs["buf"].push(
                {"temp": fields.get("temperatureC"), "rh": fields.get("humidityPct")}
            )
        else:
            refs["buf"].push(
                {
                    "pressure": fields.get("pressureHpa") or fields.get("pressurePa"),
                    "temp": fields.get("temperatureC"),
                }
            )

    # Legacy attribute aliases for app.py link-tab debug cards
    @property
    def accel(self):
        return self._bars_refs.get("accel")

    @property
    def gyro(self):
        return self._bars_refs.get("gyro")

    @property
    def euler(self):
        return self._bars_refs.get("euler") or self._bars_refs.get("orient")

    @property
    def mag(self):
        return self._bars_refs.get("mag")

    @property
    def temp(self):
        return self._bars_refs.get("temp")

    @property
    def rh(self):
        return self._bars_refs.get("rh")

    @property
    def press(self):
        return self._bars_refs.get("press")

    @property
    def body(self):
        return self._body_host
