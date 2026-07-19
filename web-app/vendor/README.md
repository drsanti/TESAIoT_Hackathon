# Offline live-data SDK

`live-data.js` is a browser ESM bundle of `@bitstream/live-data` so provider examples (`ex01`–`ex08`, `ex16`–`ex17`) work with `npx serve .` without the Bitstream Studio web-app server.

The bundled catalog includes all **six** peer sensors: BMI270, BMM350, SHT40, DPS368, ADC_POT, SW_BTN.

Refresh from Bitstream-Studio:

```bash
bash .cursor/skills/tesaiot-hackathon-hex-drop/scripts/sync-hackathon-live-data-vendor.sh
```

Or manually copy `packages/live-data/dist/live-data.browser.js` to this file.

When using **Serve Web App Folder over HTTP** in Bitstream Studio, examples load `/@bitstream/ws-live-data.js` instead.
