import { expect, test, type Page, type Route } from '@playwright/test'

/**
 * Deleting a document type, in a browser.
 *
 * Checked here rather than in a unit test because what is actually in doubt is
 * the navigation: the delete can succeed and leave the reader looking at the
 * configuration of a type that no longer exists, which reads as the delete
 * having failed.
 */

const TYPE = {
  id: 'type-1',
  name: 'Certificado JFK',
  description: 'Certificado tributario',
  extraction_prompt: 'Extraelo',
  extraction_schema: {
    type: 'object',
    properties: { issuer_nit: { type: 'string' }, saldo: { type: 'number' } }
  },
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  fields: [],
  tax_years: [],
  sample_document_id: null
}

/**
 * Where the server API lives (`nuxt.config.ts` → `serverApiBase`).
 *
 * Routes are scoped to it rather than matched with a bare `**`: the app's own
 * page lives at `/document-types/type-1` too, so a loose glob fulfils the
 * navigation itself with JSON and the screen never renders.
 */
const API = 'http://localhost:8000'

function corsHeaders(origin: string) {
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-credentials': 'true',
    'access-control-allow-headers': 'content-type',
    'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS'
  }
}

/** Answers everything the edit screen loads, plus whatever DELETE is told to do. */
async function stubServer(
  page: Page,
  baseURL: string,
  onDelete: (route: Route, headers: Record<string, string>) => Promise<void>
) {
  const headers = corsHeaders(new URL(baseURL).origin)
  const json = (body: unknown) => async (route: Route) => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    return route.fulfill({ json: body, headers })
  }

  await page.route(`${API}/auth/google/me`, json({ email: 'p@example.com', name: 'P', picture: null }))
  await page.route(`${API}/reconciliation/kinds`, json([]))
  await page.route(`${API}/reconciliation/kinds/**`, json(null))
  await page.route(`${API}/document-types?**`, json([TYPE]))
  await page.route(`${API}/document-types/type-1`, async (route) => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (route.request().method() === 'DELETE') return onDelete(route, headers)
    return route.fulfill({ json: TYPE, headers })
  })
}

async function openTheType(page: Page) {
  await page.goto('/document-types/type-1')
  await page.waitForLoadState('networkidle')
  await expect(page.getByTestId('delete-document-type')).toBeVisible()
}

test.describe('Eliminar tipo de documento', () => {
  test('takes the reader out of the type once it is gone', async ({ page, baseURL }) => {
    await stubServer(page, baseURL!, async (route, headers) =>
      route.fulfill({ status: 204, headers })
    )
    await openTheType(page)

    await page.getByTestId('delete-document-type').click()
    await page.getByTestId('confirm-delete').click()

    await expect(page).toHaveURL(/\/document-types$/)
  })

  test('does not leave the deleted type reachable by going back', async ({ page, baseURL }) => {
    await stubServer(page, baseURL!, async (route, headers) =>
      route.fulfill({ status: 204, headers })
    )
    await openTheType(page)

    await page.getByTestId('delete-document-type').click()
    await page.getByTestId('confirm-delete').click()
    await expect(page).toHaveURL(/\/document-types$/)
    await page.goBack()

    await expect(page).not.toHaveURL(/\/document-types\/type-1$/)
  })

  test('stays put and explains when documents are filed under the type', async ({
    page,
    baseURL
  }) => {
    await stubServer(page, baseURL!, async (route, headers) =>
      route.fulfill({
        status: 409,
        headers: { ...headers, 'content-type': 'application/json' },
        body: JSON.stringify({ detail: '3 document(s) are classified as type-1' })
      })
    )
    await openTheType(page)

    await page.getByTestId('delete-document-type').click()
    await page.getByTestId('confirm-delete').click()

    await expect(page.getByTestId('delete-refused')).toBeVisible()
    await expect(page).toHaveURL(/\/document-types\/type-1$/)
  })
})
