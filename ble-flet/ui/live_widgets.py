"""Live sensor visualization widgets (bars + big numbers)."""

from __future__ import annotations

import math

import flet as ft

from bs2.decode import SENSOR_LABELS


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _axis_level(value: float, span: float) -> float:
    """Map signed magnitude into 0..1 for a ProgressBar."""
    if span <= 0:
        return 0.0
    return _clamp01(abs(value) / span)


class AxisBars(ft.Column):
    """Tri-axis readout — each axis is label+value over a full-width bar.

    Do not put ProgressBar mid-Row without expand: Flet gives it zero width and the
    numeric Text can clip away (seen as blank X/Y/Z while Orientation still works).
    """

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
            rows.append(
                ft.Column(
                    [val, bar],
                    spacing=2,
                )
            )
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


class SensorLiveCard(ft.Card):
    def __init__(self, sensor_key: str) -> None:
        title = ft.Text(SENSOR_LABELS.get(sensor_key, sensor_key), weight=ft.FontWeight.W_600, size=15)
        badge = ft.Text("waiting...", size=11, color=ft.Colors.GREY_500)
        stats = ft.Text("-", size=11, color=ft.Colors.CYAN_200)
        body = ft.Column(spacing=8)

        accel = gyro = euler = mag = temp = rh = press = None

        if sensor_key == "bmi270":
            accel = AxisBars("Accel (g)", ("X", "Y", "Z"), span=2.0)
            gyro = AxisBars("Gyro (deg/s raw)", ("X", "Y", "Z"), span=250.0)
            euler = EulerTracks()
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
            body.controls = [
                ft.ResponsiveRow(
                    [
                        ft.Container(temp, col={"xs": 12, "md": 6}),
                        ft.Container(rh, col={"xs": 12, "md": 6}),
                    ],
                    spacing=8,
                ),
            ]
        else:  # dps368
            press = ScalarBar("Pressure", lo=980, hi=1040, unit="hPa", color=ft.Colors.GREEN_400)
            temp = ScalarBar("Temp", lo=0, hi=50, unit="C", color=ft.Colors.ORANGE_300)
            body.controls = [
                ft.ResponsiveRow(
                    [
                        ft.Container(press, col={"xs": 12, "md": 7}),
                        ft.Container(temp, col={"xs": 12, "md": 5}),
                    ],
                    spacing=8,
                ),
            ]

        super().__init__(
            content=ft.Container(
                padding=14,
                content=ft.Column(
                    [title, badge, stats, body],
                    spacing=6,
                ),
            ),
        )
        self.sensor_key = sensor_key
        self.title = title
        self.badge = badge
        self.stats = stats
        self.body = body
        self.accel = accel
        self.gyro = gyro
        self.euler = euler
        self.mag = mag
        self.temp = temp
        self.rh = rh
        self.press = press

    def set_stats(self, line: str, *, ok: bool | None) -> None:
        self.stats.value = line
        if ok is True:
            self.stats.color = ft.Colors.GREEN_300
        elif ok is False:
            self.stats.color = ft.Colors.ORANGE_300
        else:
            self.stats.color = ft.Colors.CYAN_200

    def set_badge(self, text: str) -> None:
        self.badge.value = text

    def apply_sample(self, sample: dict) -> None:
        fields: dict[str, float] = sample.get("fields") or {}
        key = self.sensor_key
        if key == "bmi270":
            assert self.accel and self.gyro and self.euler
            self.accel.set_xyz(fields.get("accelX"), fields.get("accelY"), fields.get("accelZ"))
            self.gyro.set_xyz(fields.get("gyroX"), fields.get("gyroY"), fields.get("gyroZ"))
            self.euler.set_fields(fields)
        elif key == "bmm350":
            assert self.mag and self.temp
            self.mag.set_xyz(fields.get("magX"), fields.get("magY"), fields.get("magZ"))
            self.temp.set_value(fields.get("temperatureC"))
        elif key == "sht40":
            assert self.temp and self.rh
            self.temp.set_value(fields.get("temperatureC"))
            self.rh.set_value(fields.get("humidityPct"))
        else:
            assert self.press and self.temp
            self.press.set_value(fields.get("pressureHpa") or fields.get("pressurePa"))
            self.temp.set_value(fields.get("temperatureC"))
