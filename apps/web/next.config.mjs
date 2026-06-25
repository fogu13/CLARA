/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    externalDir: true
  },
  async rewrites() {
    return {
      // Serve the static marketing landing (public/home.html) at the root URL,
      // keeping a clean "/" while the app lives under /dashboard, /auth, etc.
      beforeFiles: [{ source: "/", destination: "/home.html" }]
    };
  }
};

export default nextConfig;

