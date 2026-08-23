import { test, expect, type Page } from '@playwright/test'

const PHONE = { width: 375, height: 780 }
const DESKTOP = { width: 1440, height: 900 }

/**
 * Nuxt hydrates the shell after the initial paint; clicking the drawer toggle before
 * hydration lands on a DOM node with no Vue listener attached yet (see google-sign-in.spec).
 */
async function gotoAndWaitForHydration(page: Page, path = '/') {
  await page.goto(path)
  await page.waitForLoadState('networkidle')
}

/**
 * The drawer slides in and out over 200ms, and `visibility` is what takes it out of the
 * accessibility tree — so assert on visibility rather than on the transform, and let
 * Playwright's auto-retrying matchers absorb the animation.
 */
test.describe('mobile navigation drawer', () => {
  test.describe('on a phone-sized viewport', () => {
    test.use({ viewport: PHONE })

    test('is closed until the toggle is pressed, and covers the page once open', async ({ page }) => {
      await gotoAndWaitForHydration(page)

      const sidebar = page.getByTestId('app-sidebar')
      await expect(sidebar).toBeHidden()
      await expect(page.getByTestId('mobile-nav-backdrop')).toHaveCount(0)

      await page.getByTestId('mobile-nav-toggle').click()

      await expect(sidebar).toBeVisible()
      await expect(page.getByTestId('mobile-nav-backdrop')).toBeVisible()
    })

    test('closes after navigating to another section', async ({ page }) => {
      await gotoAndWaitForHydration(page)

      await page.getByTestId('mobile-nav-toggle').click()
      await page.getByRole('navigation', { name: 'main' }).getByRole('link', { name: 'Clientes' }).click()

      await expect(page).toHaveURL(/\/clients$/)
      await expect(page.getByTestId('app-sidebar')).toBeHidden()
    })

    test.describe('dismissing an open drawer', () => {
      test('closes on the close button', async ({ page }) => {
        await gotoAndWaitForHydration(page)
        await page.getByTestId('mobile-nav-toggle').click()
        await expect(page.getByTestId('app-sidebar')).toBeVisible()

        await page.getByTestId('mobile-nav-close').click()

        await expect(page.getByTestId('app-sidebar')).toBeHidden()
      })

      test('closes on Escape', async ({ page }) => {
        await gotoAndWaitForHydration(page)
        await page.getByTestId('mobile-nav-toggle').click()
        await expect(page.getByTestId('app-sidebar')).toBeVisible()

        await page.keyboard.press('Escape')

        await expect(page.getByTestId('app-sidebar')).toBeHidden()
      })

      test('closes on a tap outside it', async ({ page }) => {
        await gotoAndWaitForHydration(page)
        await page.getByTestId('mobile-nav-toggle').click()
        await expect(page.getByTestId('app-sidebar')).toBeVisible()

        await page.getByTestId('mobile-nav-backdrop').click({ position: { x: 350, y: 400 } })

        await expect(page.getByTestId('app-sidebar')).toBeHidden()
      })
    })

    test('lays every page out without horizontal overflow', async ({ page }) => {
      for (const path of ['/', '/clients', '/document-types', '/sheets']) {
        await gotoAndWaitForHydration(page, path)

        const { scrollWidth, clientWidth } = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth
        }))
        // A sub-pixel rounding difference is not a sideways-scrolling page.
        expect(scrollWidth, `${path} scrolls sideways`).toBeLessThanOrEqual(clientWidth + 1)
      }
    })
  })

  test.describe('on a desktop-sized viewport', () => {
    test.use({ viewport: DESKTOP })

    test('shows the sidebar permanently and offers no toggle', async ({ page }) => {
      await gotoAndWaitForHydration(page)

      await expect(page.getByTestId('app-sidebar')).toBeVisible()
      await expect(page.getByTestId('mobile-nav-toggle')).toBeHidden()
      await expect(page.getByTestId('mobile-nav-backdrop')).toHaveCount(0)
    })
  })
})
