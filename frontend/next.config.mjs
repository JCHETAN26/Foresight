// Static export so the dashboard deploys to any static host (GitHub Pages here).
// basePath/assetPrefix are set only for the Pages build (project site lives at
// /Foresight/); local dev and other hosts serve from the root.
const isPages = process.env.DEPLOY_TARGET === "gh-pages";
const repo = "/Foresight";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  images: { unoptimized: true },
  basePath: isPages ? repo : "",
  assetPrefix: isPages ? `${repo}/` : "",
};

export default nextConfig;
