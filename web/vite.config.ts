import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const projectRoot = "..";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, "");
  const demoMode = /^(1|true|yes|on)$/i.test(env.PUBLIC_DEMO_MODE ?? "");
  const accessToken = env.PUBLIC_DEMO_ACCESS_TOKEN ?? "";

  if (demoMode && accessToken.length < 32) {
    throw new Error(
      "PUBLIC_DEMO_ACCESS_TOKEN must contain at least 32 characters in demo mode.",
    );
  }

  return {
    envDir: projectRoot,
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: {
        "/voice": {
          target: env.PIPECAT_BACKEND_URL ?? "http://127.0.0.1:7860",
          changeOrigin: false,
          rewrite: (path) => path.replace(/^\/voice/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyRequest, request) => {
              // Never forward browser-controlled credentials or proxy identity.
              for (const header of [
                "authorization",
                "forwarded",
                "x-forwarded-for",
                "cf-connecting-ip",
              ]) {
                proxyRequest.removeHeader(header);
              }
              if (accessToken) {
                proxyRequest.setHeader("Authorization", `Bearer ${accessToken}`);
              }
              const peer = request.socket.remoteAddress;
              if (peer) proxyRequest.setHeader("CF-Connecting-IP", peer);
            });
          },
        },
      },
    },
  };
});
