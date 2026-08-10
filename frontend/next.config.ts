import type { NextConfig } from "next";

const PRODUCTION_API_URL = "https://learneros-backend.fly.dev";
const buildApiUrl = process.env.NEXT_PUBLIC_API_URL
  || (process.env.NODE_ENV === "production" ? PRODUCTION_API_URL : undefined);

const nextConfig: NextConfig = {
  env: buildApiUrl ? { NEXT_PUBLIC_API_URL: buildApiUrl } : undefined,
  async redirects() {
    return [
      {
        source: "/Walkthrough",
        destination: "/",
        permanent: false,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' https://www.gstatic.com https://www.googleapis.com https://apis.google.com https://static.cloudflareinsights.com",
              "script-src-elem 'self' 'unsafe-inline' https://www.gstatic.com https://www.googleapis.com https://apis.google.com https://static.cloudflareinsights.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com data:",
              "img-src 'self' data: blob: https:",
              "connect-src 'self' https: wss:",
              "frame-src 'self' https://teacher-b2cd9.firebaseapp.com https://*.firebaseapp.com https://accounts.google.com https://api.learneros.me https://learneros-backend.fly.dev https://assets.learneros.me",
              "frame-ancestors 'self' https://srichandra-portfolio.srichandra321.chatgpt.site",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;

import('@opennextjs/cloudflare').then(m => m.initOpenNextCloudflareForDev());
