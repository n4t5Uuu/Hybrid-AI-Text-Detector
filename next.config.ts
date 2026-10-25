import type { NextConfig } from "next";

// The detector runs in the FastAPI service (src/api); the page calls /api/* on its own origin.
const DETECTOR_API_URL = process.env.DETECTOR_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${DETECTOR_API_URL}/:path*` }];
  },
};

export default nextConfig;
