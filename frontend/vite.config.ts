import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("error", (err, _req, _res) => {
            // 开发期后端 reload 会触发 ECONNRESET，这里降噪
            if ((err as any)?.code !== "ECONNRESET") {
              console.error("[proxy error]", err);
            }
          });
        },
      },
    },
  },
});
