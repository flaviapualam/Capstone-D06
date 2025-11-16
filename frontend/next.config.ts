import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    typedRoutes: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, max-age=0',
          },
        ],
      },
    ];
  },
  async rewrites() {
    // Route client-side /api requests through Next.js to the backend.
    // This avoids mixed-content / CORS issues during development when the
    // backend is hosted on a different origin. The destination uses the
    // NEXT_PUBLIC_API_URL env var when present; otherwise falls back to the
    // known backend address.
    const backendBase = process.env.NEXT_PUBLIC_API_URL || 'http://103.181.143.162:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
