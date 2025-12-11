import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  server: {
    allowedHosts: ["localhost", "trading.evoagents.cn","www.evoagents.cn"]
  },
  plugins: [react(), tsconfigPaths(),tailwindcss()],
  preview: {
    host: "0.0.0.0",
    port: 4173
  },
});

