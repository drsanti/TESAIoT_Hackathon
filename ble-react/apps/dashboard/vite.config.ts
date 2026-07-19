import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    host: "localhost",
  },
  resolve: {
    alias: {
      "@ternion/tbs-core": path.resolve(root, "../../packages/tbs-core/src/index.ts"),
      "@ternion/tbs-ble-session": path.resolve(
        root,
        "../../packages/tbs-ble-session/src/index.ts",
      ),
    },
  },
});
