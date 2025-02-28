/** @type {import('next').NextConfig} */
const nextConfig = {
  rewrites: async () => {
    return [
      {
        source: '/api/post_info',
        destination: '/api/post_info'
      },
      {
        source: '/api/top_phrases',
        destination: '/api/top_phrases'
      },
    ];
  },
  
  images: {
    domains: ['lh3.googleusercontent.com'],
  },
  
  env: {
    NEXTAUTH_URL: process.env.NEXTAUTH_URL,
  }
}

module.exports = nextConfig;
