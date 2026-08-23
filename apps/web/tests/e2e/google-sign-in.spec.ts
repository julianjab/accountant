import { test, expect, type Page } from '@playwright/test'

const USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

interface MockGisOptions {
  scope: 'granted' | 'denied' | 'popupClosed'
  email?: string
  name?: string
}

/**
 * Stubs `window.google.accounts.oauth2` (Google Identity Services) before the app
 * hydrates, so the real token/consent flow never has to reach accounts.google.com.
 */
async function mockGoogleIdentity(page: Page, options: MockGisOptions) {
  if (options.scope === 'granted') {
    await page.route(`${USERINFO_URL}**`, route =>
      route.fulfill({
        json: { email: options.email, name: options.name, picture: null }
      })
    )
  }

  await page.addInitScript((opts) => {
    window.google = {
      accounts: {
        oauth2: {
          initTokenClient: (config: {
            callback: (response: Record<string, unknown>) => void
            error_callback?: (error: { type: string }) => void
          }) => ({
            requestAccessToken: () => {
              if (opts.scope === 'popupClosed') {
                config.error_callback?.({ type: 'popup_closed' })
                return
              }
              config.callback({ access_token: 'fake-access-token', expires_in: 3600 })
            }
          }),
          hasGrantedAllScopes: () => opts.scope === 'granted',
          revoke: (_token: string, callback?: () => void) => callback?.()
        }
      }
    }
  }, options)
}

/**
 * Nuxt hydrates the header after the initial paint; clicking before hydration lands on a
 * DOM node with no Vue listener attached yet, so wait for the network to settle first.
 */
async function gotoAndWaitForHydration(page: Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
}

test.describe('Google sign-in', () => {
  test('shows the sign-in button when logged out', async ({ page }) => {
    await gotoAndWaitForHydration(page)

    await expect(page.getByTestId('google-auth-sign-in')).toBeVisible()
    await expect(page.getByTestId('google-auth-signed-in-as')).toHaveCount(0)
  })

  test('signs in, shows the user email, and signs back out', async ({ page }) => {
    await mockGoogleIdentity(page, { scope: 'granted', email: 'preparer@example.com', name: 'Preparer' })
    await gotoAndWaitForHydration(page)

    await page.getByTestId('google-auth-sign-in').click()

    await expect(page.getByTestId('google-auth-signed-in-as')).toContainText('preparer@example.com')
    await expect(page.getByTestId('google-auth-sign-in')).toHaveCount(0)

    await page.getByTestId('google-auth-sign-out').click()

    await expect(page.getByTestId('google-auth-sign-in')).toBeVisible()
    await expect(page.getByTestId('google-auth-signed-in-as')).toHaveCount(0)
  })

  test('shows an error and stays signed out when the Drive scope is not granted', async ({ page }) => {
    await mockGoogleIdentity(page, { scope: 'denied' })
    await gotoAndWaitForHydration(page)

    await page.getByTestId('google-auth-sign-in').click()

    await expect(page.getByTestId('google-auth-error')).toContainText('Drive')
    await expect(page.getByTestId('google-auth-sign-in')).toBeVisible()
  })

  test('shows an error when the Google popup is closed before completing sign-in', async ({ page }) => {
    await mockGoogleIdentity(page, { scope: 'popupClosed' })
    await gotoAndWaitForHydration(page)

    await page.getByTestId('google-auth-sign-in').click()

    await expect(page.getByTestId('google-auth-error')).toContainText('ventana')
    await expect(page.getByTestId('google-auth-sign-in')).toBeVisible()
  })
})
