import { defineConfig, devices } from '@playwright/test'

// A dedicated port (not the usual :3000) so this suite's own dev server -- started below
// with a mock client id -- never gets shadowed by a developer's already-running `bun run dev`.
const DEFAULT_BASE_URL = 'http://localhost:3100'
const explicitBaseURL = process.env.PLAYWRIGHT_BASE_URL
const baseURL = explicitBaseURL ?? DEFAULT_BASE_URL

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
  // window.google, so the specs need a (fake, mock-only) client id configured. Skipped when
  // PLAYWRIGHT_BASE_URL points at an already-running target (e.g. a remote/staging server).
  webServer: explicitBaseURL
    ? undefined
    : {
        command: `bun run dev -- --port ${new URL(DEFAULT_BASE_URL).port}`,
        url: DEFAULT_BASE_URL,
        reuseExistingServer: false,
        env: { NUXT_PUBLIC_GOOGLE_CLIENT_ID: 'e2e-fake-client-id.apps.googleusercontent.com' }
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
