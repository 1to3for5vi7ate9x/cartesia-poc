import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { VitePWA } from 'vite-plugin-pwa' // Import the plugin

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    VitePWA({ // Add the plugin configuration
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'Cartesia Mobile App',
        short_name: 'CartesiaApp',
        description: 'Mobile PWA using Cartesia SSM',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'pwa-192x192.png', // Placeholder icon
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png', // Placeholder icon
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png', // Placeholder for maskable icon
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'], // Cache app shell assets
        cleanupOutdatedCaches: true, // Remove old caches
        runtimeCaching: [ // Add runtime caching for API calls
          {
            urlPattern: ({ url }) => url.pathname === '/api/process-request', // Match our API endpoint
            handler: 'NetworkFirst', // Try network first, fallback to cache
            options: {
              cacheName: 'api-cache', // Name for this cache
              expiration: {
                maxEntries: 10, // Max number of responses to cache
                maxAgeSeconds: 60 * 60 * 24 * 7 // Cache for 1 week
              },
              cacheableResponse: {
                statuses: [0, 200], // Cache successful responses and opaque responses (for no-cors potentially)
              },
            },
          },
        ],
      }
    })
  ],
})
