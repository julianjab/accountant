import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000'

export default defineConfig({
  testDir: './tests/e2e',
  // The Nuxt dev server compiles routes on first request; concurrent workers racing that
  // compile made `networkidle` waits flaky. Serialize until this suite targets a built app.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list']],
  use: {
    baseURL,
    // Pin the browser locale so specs can assert on the (Spanish) default-locale copy
    // instead of racing @nuxtjs/i18n's browser-language auto-detection.
    locale: 'es-ES',
    trace: 'retain-on-failure'
  },
  // The sign-in flow bails out with a "missing client id" error before ever touching
  // window.google, so the specs need a (fake, mock-only) client id configured.
  webServer: {
    command: 'bun run dev -- --port ' + new URL(baseURL).port,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    env: { NUXT_PUBLIC_GOOGLE_CLIENT_ID: 'e2e-fake-client-id.apps.googleusercontent.com' }
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
