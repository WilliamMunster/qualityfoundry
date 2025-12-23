import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite 配置（MVP）
 * - 先保持最小配置：React 插件
 * - 后续如要做同源代理（避免 CORS），可在这里加 server.proxy
 */
export default defineConfig({
  plugins: [react()]
});
