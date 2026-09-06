import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the docker image copies the standalone server, not node_modules
  output: "standalone",
};

export default nextConfig;
