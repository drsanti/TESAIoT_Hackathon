"""Flet UI for TESAIoT BLE BS2 dashboard."""

from __future__ import annotations

import flet as ft
from bleak.backends.device import BLEDevice

from bs2 import Bs2BleSession, SessionState
from bs2.decode import SENSOR_LABELS


def _fmt_fields(fields: dict[str, float]) -> str:
    if not fields:
        return "—"
    parts: list[str] = []
    for key, value in fields.items():
        parts.append(f"{key}={value:.2f}")
    return " · ".join(parts[:6])


class BleDashboardApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.devices: list[BLEDevice] = []
        self.session = Bs2BleSession(
            on_log=self._on_log,
            on_sample=self._on_sample,
            on_state=self._on_state,
        )

        self.device_dropdown = ft.Dropdown(
            label="Peripheral",
            width=280,
            options=[],
            disabled=True,
        )
        self.status_text = ft.Text("Disconnected", color=ft.Colors.GREY_400)
        self.policy_text = ft.Text("policy —", size=12, color=ft.Colors.GREY_500)
        self.link_text = ft.Text("BS_LINK —", size=12, color=ft.Colors.GREY_500)
        self.log_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        self.sensor_tiles: dict[str, ft.Card] = {}
        self.sensor_meta: dict[str, ft.Text] = {}
        self.sensor_values: dict[str, ft.Text] = {}

        for key in ("bmi270", "bmm350", "sht40", "dps368"):
            meta = ft.Text("waiting…", size=11, color=ft.Colors.GREY_500)
            values = ft.Text("—", size=13)
            self.sensor_meta[key] = meta
            self.sensor_values[key] = values
            self.sensor_tiles[key] = ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        [
                            ft.Text(SENSOR_LABELS[key], weight=ft.FontWeight.W_600, size=14),
                            meta,
                            values,
                        ],
                        spacing=6,
                    ),
                ),
            )

    def build(self) -> ft.Control:
        scan_btn = ft.ElevatedButton("Scan", icon=ft.Icons.BLUETOOTH_SEARCHING, on_click=self._scan)
        connect_btn = ft.ElevatedButton("Connect", icon=ft.Icons.LINK, on_click=self._connect)
        disconnect_btn = ft.OutlinedButton("Disconnect", on_click=self._disconnect)
        stream_btn = ft.FilledButton("Stream on", icon=ft.Icons.PLAY_ARROW, on_click=self._stream_on)
        hz_btn = ft.OutlinedButton("Apply 1 Hz", on_click=self._apply_1hz)
        ping_btn = ft.OutlinedButton("PING", on_click=self._ping)
        link_btn = ft.OutlinedButton("BS_LINK", on_click=self._read_link)

        toolbar = ft.Row(
            [scan_btn, self.device_dropdown, connect_btn, disconnect_btn, stream_btn, hz_btn, ping_btn, link_btn],
            wrap=True,
            spacing=8,
        )

        status_row = ft.Column([self.status_text, self.policy_text, self.link_text], spacing=2)

        sensor_grid = ft.ResponsiveRow(
            [ft.Container(self.sensor_tiles[k], col={"xs": 12, "md": 6}) for k in self.sensor_tiles],
            spacing=10,
            run_spacing=10,
        )

        return ft.Column(
            [
                ft.Text("TESAIoT BLE Dashboard", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Desktop BS2 over BLE (bleak). Firmware BLE module profile required.",
                    size=13,
                    color=ft.Colors.GREY_400,
                ),
                toolbar,
                status_row,
                sensor_grid,
                ft.Text("Log", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_500),
                ft.Container(
                    content=self.log_list,
                    height=160,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=8,
                ),
            ],
            expand=True,
            spacing=12,
        )

    def _on_log(self, level: str, text: str) -> None:
        color = ft.Colors.GREY_300
        if level == "error":
            color = ft.Colors.RED_300
        elif level == "info":
            color = ft.Colors.GREEN_200
        self.log_list.controls.append(ft.Text(text, size=12, color=color))
        if len(self.log_list.controls) > 200:
            self.log_list.controls.pop(0)
        self.page.update()

    def _on_sample(self, sample: dict) -> None:
        key = sample["sensor"]
        meta = self.session.format_sample_meta(sample)
        vals = _fmt_fields(sample.get("fields", {}))
        if self.sensor_meta[key].value == meta and self.sensor_values[key].value == vals:
            return
        self.sensor_meta[key].value = meta
        self.sensor_values[key].value = vals
        self.page.update()

    def _on_state(self, state: SessionState) -> None:
        """Connection / policy / BS_LINK chrome only — not sensor cards."""
        if state.connected:
            self.status_text.value = f"Connected — {state.device_name} ({state.device_address})"
            self.status_text.color = ft.Colors.GREEN_300
        else:
            self.status_text.value = "Disconnected"
            self.status_text.color = ft.Colors.GREY_400
        pol = state.policy_flags
        self.policy_text.value = (
            f"policy 0x{pol:02x} "
            f"({'TX_EVT' if pol & 0x02 else 'no EVT'})"
            f"{' · streaming' if state.streaming else ''}"
        )
        self.link_text.value = (
            f"BS_LINK state={state.link_state} mtu={state.link_mtu} tx_drops={state.link_tx_drops}"
        )
        self.page.update()

    async def _scan(self, _e: ft.ControlEvent) -> None:
        self._on_log("info", "Scanning for TESAIoT-* …")
        self.devices = await self.session.scan(timeout=8.0)
        self.device_dropdown.options = [
            ft.dropdown.Option(key=d.address, text=f"{d.name or 'TESAIoT'} ({d.address})")
            for d in self.devices
        ]
        self.device_dropdown.disabled = len(self.devices) == 0
        if self.devices:
            self.device_dropdown.value = self.devices[0].address
        self.page.update()

    def _device_by_address(self, address: str | None) -> BLEDevice | None:
        if not address:
            return None
        for device in self.devices:
            if device.address == address:
                return device
        return None

    async def _connect(self, _e: ft.ControlEvent) -> None:
        device = self._device_by_address(self.device_dropdown.value)
        if device is None:
            self._on_log("error", "Select a peripheral after Scan")
            return
        try:
            await self.session.connect(device)
        except Exception as exc:
            self._on_log("error", f"Connect failed: {exc}")

    async def _disconnect(self, _e: ft.ControlEvent) -> None:
        await self.session.disconnect()

    async def _stream_on(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.enable_streaming()
        except Exception as exc:
            self._on_log("error", f"Stream on failed: {exc}")

    async def _apply_1hz(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.apply_1hz_lab()
            self._on_log("info", "All sensors set to 1 Hz (RAM until reboot)")
        except Exception as exc:
            self._on_log("error", f"Apply 1 Hz failed: {exc}")

    async def _ping(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.ping()
            self._on_log("info", "PING OK")
        except Exception as exc:
            self._on_log("error", f"PING failed: {exc}")

    async def _read_link(self, _e: ft.ControlEvent) -> None:
        try:
            await self.session.read_link_snapshot()
        except Exception as exc:
            self._on_log("error", f"BS_LINK read failed: {exc}")
