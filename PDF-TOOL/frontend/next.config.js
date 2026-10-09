/** @type {import('next').NextConfig} */
// `npm run build:desktop` → static site in ./out, served by the local Python engine.
// Plain `npm run dev` / `npm run build` keep working as before.
const isDesktop = process.env.PDFTOOL_DESKTOP === "1";
const nextConfig = isDesktop
  ? { output: "export", trailingSlash: true, images: { unoptimized: true } }
  : {};
module.exports = nextConfig;
