"""Live sensor visualization widgets (bars, lines, big numbers)."""

from __future__ import annotations

import math
from typing import Callable

import flet as ft

from bs2.decode import SENSOR_LABELS
from ui.charts import LineSeriesChart, MultiSeriesBuffer
from ui.theme import SENSOR_STRIPE, plot_mode_toggle


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _axis_level(value: float, span: float) -> float:
    if span <= 0:
        return 0.0
    return _clamp01(abs(value) / span)


class AxisBars(ft.Column):
    def __init__(self, title: str, labels: tuple[str, str, str], *, span: float) -> None:
        bars: list[ft.ProgressBar] = []
        vals: list[ft.Text] = []
        rows: list[ft.Control] = [
            ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_400),
        ]
        bar_colors = (ft.Colors.CYAN_400, ft.Colors.TEAL_300, ft.Colors.AMBER_300)
        for i, lab in enumerate(labels):
            val = ft.Text(f"{lab}  -", size=13, color=ft.Colors.GREY_200)
            bar = ft.ProgressBar(
                value=0,
                bar_height=10,
                color=bar_colors[i],
                bgcolor=ft.Colors.GREY_800,
            )
            bars.append(bar)
            vals.append(val)
            rows.append(ft.Column([val, bar], spacing=2))
        super().__init__(rows, spacing=6, expand=True)
        self._span = span
        self._labels = labels
        self._bars = bars
        self._vals = vals

    def set_xyz(self, x: float | None, y: float | None, z: float | None) -> None:
        for i, raw in enumerate((x, y, z)):
            lab = self._labels[i]
            if raw is None:
                self._bars[i].value = 0
                self._vals[i].value = f"{lab}  -"
                self._vals[i].color = ft.Colors.GREY_500
            else:
                self._bars[i].value = _axis_level(raw, self._span)
                self._vals[i].value = f"{lab}  {raw:+.2f}"
                self._vals[i].color = ft.Colors.GREY_100


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
        big = ft.Text("-", size=28, weight=ft.FontWeight.W_600)
        bar = ft.ProgressBar(value=0, bar_height=12, color=color, bgcolor=ft.Colors.GREY_800)
        super().__init__(
            [
                ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_400),
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
            self._big.value = "-"
            self._bar.value = 0
            return
        self._big.value = f"{value:.1f} {self._unit}"
        span = self._hi - self._lo
        self._bar.value = _clamp01((value - self._lo) / span) if span else 0


class EulerTracks(ft.Column):
    def __init__(self) -> None:
        heading = ft.ProgressBar(value=0.5, bar_height=8, color=ft.Colors.PURPLE_300, bgcolor=ft.Colors.GREY_800)
        pitch = ft.ProgressBar(value=0.5, bar_height=8, color=ft.Colors.INDIGO_300, bgcolor=ft.Colors.GREY_800)
        roll = ft.ProgressBar(value=0.5, bar_height=8, color=ft.Colors.PINK_300, bgcolor=ft.Colors.GREY_800)
        h_txt = ft.Text("heading -", size=11, color=ft.Colors.GREY_300)
        p_txt = ft.Text("pitch -", size=11, color=ft.Colors.GREY_300)
        r_txt = ft.Text("roll -", size=11, color=ft.Colors.GREY_300)
        quat = ft.Text("quat -", size=11, color=ft.Colors.GREY_500)
        super().__init__(
            [
                ft.Text("Orientation", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_400),
                h_txt,
                heading,
                p_txt,
                pitch,
                r_txt,
                roll,
                quat,
            ],
            spacing=3,
        )
        self._heading = heading
        self._pitch = pitch
        self._roll = roll
        self._h_txt = h_txt
        self._p_txt = p_txt
        self._r_txt = r_txt
        self._quat = quat

    def set_fields(self, fields: dict[str, float]) -> None:
        def deg(rad_key: str) -> float | None:
            if rad_key not in fields:
                return None
            return fields[rad_key] * (180.0 / math.pi)

        h = deg("headingRad")
        p = deg("pitchRad")
        r = deg("rollRad")
        if h is None:
            self._h_txt.value = "heading -"
            self._heading.value = 0.5
        else:
            wrapped = h % 360.0
            self._h_txt.value = f"heading {wrapped:.0f} deg"
            self._heading.value = _clamp01(wrapped / 360.0)
        if p is None:
            self._p_txt.value = "pitch -"
            self._pitch.value = 0.5
        else:
            self._p_txt.value = f"pitch {p:+.0f} deg"
            self._pitch.value = _clamp01((p + 90.0) / 180.0)
        if r is None:
            self._r_txt.value = "roll -"
            self._roll.value = 0.5
        else:
            self._r_txt.value = f"roll {r:+.0f} deg"
            self._roll.value = _clamp01((r + 90.0) / 180.0)

        qw = fields.get("quatW")
        qx = fields.get("quatX")
        qy = fields.get("quatY")
        qz = fields.get("quatZ")
        if qw is None:
            self._quat.value = "quat -"
        else:
            self._quat.value = f"quat {qw:.2f} · {qx or 0:.2f} · {qy or 0:.2f} · {qz or 0:.2f}"


def _build_bars_body(sensor_key: str) -> tuple[ft.Column, dict]:
    refs: dict = {}
    body = ft.Column(spacing=8)
    if sensor_key == "bmi270":
        accel = AxisBars("Accel (g)", ("X", "Y", "Z"), span=2.0)
        gyro = AxisBars("Gyro (deg/s raw)", ("X", "Y", "Z"), span=250.0)
        euler = EulerTracks()
        refs = {"accel": accel, "gyro": gyro, "euler": euler}
        body.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(accel, col={"xs": 12, "md": 6}),
                    ft.Container(gyro, col={"xs": 12, "md": 6}),
                ],
                spacing=8,
            ),
            euler,
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
    body = ft.Column(spacing=8, expand=True)
    if sensor_key == "bmi270":
        accel_buf = MultiSeriesBuffer(("X", "Y", "Z"))
        gyro_buf = MultiSeriesBuffer(("X", "Y", "Z"))
        euler_buf = MultiSeriesBuffer(("heading", "pitch", "roll"))
        accel_chart = LineSeriesChart(
            title="Accel (g)",
            y_min=-2,
            y_max=2,
            height=120,
            series_labels=("X", "Y", "Z"),
        )
        gyro_chart = LineSeriesChart(
            title="Gyro",
            y_min=-250,
            y_max=250,
            height=120,
            series_labels=("X", "Y", "Z"),
        )
        euler_chart = LineSeriesChart(
            title="Euler (deg)",
            y_min=-180,
            y_max=360,
            height=100,
            series_labels=("heading", "pitch", "roll"),
        )
        refs = {
            "accel_buf": accel_buf,
            "gyro_buf": gyro_buf,
            "euler_buf": euler_buf,
            "accel_chart": accel_chart,
            "gyro_chart": gyro_chart,
            "euler_chart": euler_chart,
        }
        body.controls = [
            ft.ResponsiveRow(
                [
                    ft.Container(accel_chart, col={"xs": 12, "md": 6}),
                    ft.Container(gyro_chart, col={"xs": 12, "md": 6}),
                ],
                spacing=8,
            ),
            euler_chart,
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
            size=15,
        )
        self._badge_text = ft.Text("waiting...", size=11, color=ft.Colors.GREY_500)
        self._stats_text = ft.Text("-", size=11, color=ft.Colors.CYAN_200)
        self._plot_toggle_host = ft.Container()

        self._bars_body, self._bars_refs = _build_bars_body(sensor_key)
        self._lines_body: ft.Column | None = None
        self._lines_refs: dict = {}
        self._body_host = ft.Container(expand=True)

        super().__init__(
            content=ft.Column(
                [
                    self._header_row(),
                    self._badge_text,
                    self._stats_text,
                    self._body_host,
                ],
                spacing=6,
            ),
            bgcolor="#12121A",
            border=ft.Border(
                left=ft.BorderSide(3, stripe),
                top=ft.BorderSide(1, "#38384A"),
                right=ft.BorderSide(1, "#38384A"),
                bottom=ft.BorderSide(1, "#38384A"),
            ),
            border_radius=10,
            padding=14,
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
                ft.Container(expand=True),
                self._plot_toggle_host,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
        self._title_text.size = 13 if compact else 15
        self._stats_text.visible = not compact
        self._badge_text.visible = not compact

    def set_stats(self, line: str, *, ok: bool | None) -> None:
        self._stats_text.value = line
        if ok is True:
            self._stats_text.color = ft.Colors.GREEN_300
        elif ok is False:
            self._stats_text.color = ft.Colors.ORANGE_300
        else:
            self._stats_text.color = ft.Colors.CYAN_200

    def set_badge(self, text: str) -> None:
        self._badge_text.value = text

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
            refs["accel"].set_xyz(fields.get("accelX"), fields.get("accelY"), fields.get("accelZ"))
            refs["gyro"].set_xyz(fields.get("gyroX"), fields.get("gyroY"), fields.get("gyroZ"))
            refs["euler"].set_fields(fields)
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
                    "heading": (h * 180 / math.pi) if h is not None else None,
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
        return self._bars_refs.get("euler")

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
