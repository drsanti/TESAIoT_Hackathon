# Lab 01 — Browser ready

## Goal

Confirm the browser can use Web Bluetooth before any GATT work.

## On-screen steps

1. **Secure context** — page must be `https` or `http://localhost`.
2. **Web Bluetooth API** — `navigator.bluetooth.requestDevice` available (Chrome/Edge).

## Acceptance

Both checks green → chapter complete → continue to Lab 02.

## Notes

Safari and Firefox do not support Web Bluetooth. Do not open `file://` builds. Use system Chrome/Edge, not Cursor’s embedded browser, for later GATT chapters.
