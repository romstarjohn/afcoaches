/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

const backend = 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // "prompt": a new version never reloads the app by surprise while the user is typing offline data.
      registerType: 'prompt',
      injectRegister: false, // registered from React via virtual:pwa-register/react
      pwaAssets: {
        image: 'public/logo.svg',
        preset: 'minimal-2023',
        overrideManifestIcons: true,
      },
      manifest: {
        id: '/',
        name: 'Coach sur mesure',
        short_name: 'Coach',
        description: 'Coaching sportif et nutritionnel ancré dans la cuisine d’Afrique de l’Ouest.',
        lang: 'fr',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#fffaf5',
        theme_color: '#b5541c',
      },
      workbox: {
        // App shell only. API responses are NEVER cached by the service worker: personal/health data
        // lives in IndexedDB under app control, so it can be wiped on logout.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest,woff2}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/static\//, /^\/healthz/],
        cleanupOutdatedCaches: true,
        runtimeCaching: [],
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 5173,
    // Same-origin in development too: session cookie + CSRF work exactly like in production.
    proxy: {
      '/api': backend,
      '/admin': backend,
      '/static': backend,
      '/healthz': backend,
    },
  },
  build: { sourcemap: true },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
  },
})
