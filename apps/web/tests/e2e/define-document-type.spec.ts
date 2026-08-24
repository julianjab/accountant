import { test, expect, type Page } from '@playwright/test'

/**
 * The proposal the AI would return for a bank certificate: two blocks of the
 * paper, one identifier, two amounts and one piece of surrounding prose.
 */
const PROPOSAL = {
  extraction_prompt: 'Extrae los campos del certificado',
  extraction_schema: {
    type: 'object',
    properties: {
      nit_entidad: { type: 'string' },
      razon_social: { type: 'string' },
      gmf: { type: 'number' },
      saldo: { type: 'number' },
      pie_de_pagina: { type: 'string' }
    }
  },
  fields: [
    {
      path: 'nit_entidad',
      label: 'NIT de la entidad',
      role: 'identifier',
      sample_value: '890903938',
      section: 'Datos de la entidad'
    },
    {
      path: 'razon_social',
      label: 'Razón social',
      role: 'context',
      sample_value: 'BANCOLOMBIA S.A.',
      section: 'Datos de la entidad'
    },
    {
      path: 'gmf',
      label: 'Valor GMF',
      role: 'amount',
      sample_value: '512.561,52',
      section: 'Gravamen a los movimientos financieros'
    },
    {
      path: 'saldo',
      label: 'Saldo a 31 de diciembre',
      role: 'amount',
      sample_value: '2.241.275,17',
      section: 'Cuentas de ahorro'
    },
    {
      path: 'pie_de_pagina',
      label: 'Nota al pie',
      role: 'context',
      sample_value: 'Documento generado automáticamente',
      section: ''
    }
  ],
  field_mappings: [
    { field_path: 'gmf', concept_id: 'bank:gmf', account_path: null, sign: -1 },
    { field_path: 'saldo', concept_id: 'bank:saldo', account_path: null, sign: 1 }
  ],
  unmapped_fields: [],
  kind_id: 'exogena_dian',
  reporter_path: 'nit_entidad',
  reporter_name_path: 'razon_social',
  period_path: null
}

const CREATED = {
  id: 'dt-1',
  name: 'Certificado Bancolombia',
  description: 'Certificado tributario',
  extraction_prompt: PROPOSAL.extraction_prompt,
  extraction_schema: PROPOSAL.extraction_schema,
  active: true,
  created_at: '2026-08-24T00:00:00Z',
  fields: [],
  mapping_changes: []
}

/**
 * The app calls the server cross-origin with credentials, so a stubbed
 * response without the CORS headers is rejected by the browser before the page
 * ever sees it — the stub has to answer the preflight too.
 */
function corsHeaders(origin: string) {
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-credentials': 'true',
    'access-control-allow-headers': 'content-type',
    'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS'
  }
}

async function stubServer(page: Page, baseURL: string) {
  const headers = corsHeaders(new URL(baseURL).origin)
  const respond = (json: unknown) => (route: import('@playwright/test').Route) =>
    route.request().method() === 'OPTIONS'
      ? route.fulfill({ status: 204, headers })
      : route.fulfill({ json, headers })

  await page.route('**/document-types/proposals', respond(PROPOSAL))
  await page.route('**/document-types', respond(CREATED))
}

async function proposeFromSample(page: Page) {
  await page.goto('/document-types/new?issuer=Bancolombia&claim=GMF&document=doc-1')
  // Submitting before Nuxt hydrates runs the form's native GET, which reloads the
  // page and clears everything typed (see mobile-navigation.spec).
  await page.waitForLoadState('networkidle')
  await page.getByRole('textbox', { name: 'Nombre' }).fill('Certificado Bancolombia')
  await page.getByRole('textbox', { name: 'Descripción' }).fill('Certificado tributario')
  await page.locator('input[type=file]').setInputFiles({
    name: 'certificado.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 sample')
  })
  await page.getByRole('button', { name: 'Analizar documento' }).click()
  await expect(page.getByTestId('proposal-sections')).toBeVisible()
}

test.describe('Definir tipo de documento', () => {
  test.beforeEach(async ({ page, baseURL }) => {
    await stubServer(page, baseURL!)
  })

  test('groups the proposed fields the way the document reads', async ({ page }) => {
    await proposeFromSample(page)

    const sections = page.getByTestId('proposal-sections').locator('> section')
    await expect(sections).toHaveCount(4)
    await expect(sections.nth(0)).toContainText('Datos de la entidad')
    await expect(sections.nth(3)).toContainText('Otros campos del documento')
    await expect(page.getByText('En la muestra: 512.561,52')).toBeVisible()
  })

  test('starts with the identification and the amounts selected', async ({ page }) => {
    await proposeFromSample(page)

    await expect(page.getByTestId('kept-summary')).toHaveText(
      'Se van a extraer 3 de 5 campos.'
    )
    const checkboxes = page.getByTestId('proposal-sections').getByRole('checkbox')
    await expect(checkboxes.nth(0)).toBeChecked()
    await expect(checkboxes.nth(1)).not.toBeChecked()
  })

  test('selects and clears a whole section at once', async ({ page }) => {
    await proposeFromSample(page)

    const section = page.getByTestId('proposal-sections').locator('> section').first()
    await section.getByRole('button', { name: 'Marcar todo' }).click()
    await expect(section).toContainText('2 de 2 marcados')
    await section.getByRole('button', { name: 'Ninguno' }).click()
    await expect(section).toContainText('0 de 2 marcados')
  })

  test('blocks saving when the field holding the tax id is unselected', async ({ page }) => {
    await proposeFromSample(page)

    await page
      .getByTestId('proposal-sections')
      .getByRole('checkbox')
      .nth(0)
      .uncheck()

    await expect(page.getByTestId('reporter-missing')).toBeVisible()
    await expect(page.getByTestId('create-document-type')).toBeDisabled()
  })

  test('creates the type and offers to configure the reconciliation', async ({ page }) => {
    await proposeFromSample(page)

    await page.getByTestId('create-document-type').click()

    await expect(page.getByText('Se creó «Certificado Bancolombia»')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Ajustar la conciliación' })).toHaveAttribute(
      'href',
      '/document-types/dt-1'
    )
  })
})
