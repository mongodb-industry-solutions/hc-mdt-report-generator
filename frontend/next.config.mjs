/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode
  reactStrictMode: true,
  
  // Output configuration for static export if needed
  output: 'standalone',
  
  // Turbopack configuration (Next.js 16+ default)
  turbopack: {
    // Set root directory to silence workspace warning
    root: process.cwd(),
  },
  
  // Image optimization
  images: {
    unoptimized: true,
  },
  
  // Disable x-powered-by header for security
  poweredByHeader: false,
  
  // Compression
  compress: true,
};

export default nextConfig;