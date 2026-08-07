import type { NextConfig } from "next";

// Do not set `output: "standalone"` — it breaks Vercel builds
// (missing .next/next-server.js.nft.json). Vercel handles hosting natively.
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
};

export default nextConfig;