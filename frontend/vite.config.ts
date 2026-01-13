import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import http from "http";

const agent = new http.Agent({
  keepAlive: true,
  timeout: 300000,
});

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        timeout: 300000,
        proxyTimeout: 300000,
        agent: agent,
        configure: (proxy) => {
          proxy.on("error", (err, _req, _res) => {
            console.error("[proxy error]", err);
          });
        },
      },
    },
  },
});
