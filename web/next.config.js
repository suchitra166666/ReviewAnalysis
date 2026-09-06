/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    const api = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [{ source: "/backend/:path*", destination: `${api.replace(/\/$/, "")}/:path*` }];
  },
};

module.exports = nextConfig;
