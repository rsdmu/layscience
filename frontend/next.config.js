/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { typedRoutes: true },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://layscience.onrender.com/api/:path*",
      },
    ];
  },
};
module.exports = nextConfig;
