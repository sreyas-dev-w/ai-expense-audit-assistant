import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo root also has a package-lock.json (for the shadcn CLI dev
  // dependency), which makes Turbopack guess the wrong workspace root.
  // apps/web is the actual Next.js project root.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
