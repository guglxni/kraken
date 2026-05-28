import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode for catching potential issues early
  reactStrictMode: true,

  // Use Turbopack for faster development builds
  turbopack: {},
};

export default nextConfig;
