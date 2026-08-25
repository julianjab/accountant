import { expect, test, type Page, type Route } from '@playwright/test'

/**
 * Iterating a regeneration, in a browser.
 *
 * Checked here rather than in a unit test because what is in doubt is the
 * screen itself: a regeneration is decided by reading two lists against each
 * other — what the type extracts today, and what it would extract if this
 * reading were applied — and every failure of this feature has been a failure
 * to show which fields are about to be lost, or to show both lists at once so
 * that neither could be read.
 */

const TYPE = {
  id: 'type-1',
  name: 'Certificado Bancolombia',
  description: 'Certificado tributario',
  extraction_prompt: 'Extrae los campos del certificado',
  extraction_schema: {
    type: 'object',
    properties: {
      nit_entidad: { type: 'string' },
      gmf: { type: 'number' },
      base_gravable: { type: 'number' }
    }
  },
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  fields: [
    {
      path: 'nit_entidad',
      label: 'NIT de la entidad',
      role: 'identifier',
      section: 'Datos de la entidad',
      sample_value: '890903938'
    },
    {
      path: 'gmf',
      label: 'Valor GMF',
      role: 'amount',
      section: 'Gravamen a los movimientos financieros',
      sample_value: '512.561,52'
    },
    {
      path: 'base_gravable',
      label: 'Base gravable del GMF',
      // No role stored, as every type configured before roles were carried:
      // the path is what has to say this is money.
      role: 'context',
      section: 'Gravamen a los movimientos financieros',
      sample_value: '2241275.17'
    }
  ],
  tax_years: [],
  sample_document_id: 'doc-1'
}

/** The paper the type was configured from, which is what it is read again from. */
const SAMPLE = {
  id: 'doc-1',
  client_id: 'client-1',
  document_type_id: 'type-1',
  drive_file_id: 'drive-1',
  file_name: 'Bancolombia_cuenta.pdf',
  mime_type: 'application/pdf',
  status: 'approved',
  error: null,
  created_at: '2026-01-01T00:00:00Z',
  processed_at: '2026-01-01T00:00:00Z',
  reviewed_at: null,
  approved_by: null,
  source_id: null
}

/**
 * A reading that gains a field and loses one: `base_gravable` is gone and
 * `fecha_expedicion` is new. The state a certificate actually lands in, and
 * the one an all-or-nothing apply had no answer for.
 */
const PROPOSAL = {
  extraction_prompt: 'Extrae los campos del certificado, con la fecha',
  extraction_schema: {
    type: 'object',
    properties: {
      nit_entidad: { type: 'string' },
      gmf: { type: 'number' },
      fecha_expedicion: { type: 'string' }
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
      path: 'gmf',
      label: 'Valor GMF',
      role: 'amount',
      sample_value: '512561.52',
      section: 'Gravamen a los movimientos financieros'
    },
    {
      path: 'fecha_expedicion',
      label: 'Fecha de expedición',
      role: 'context',
      sample_value: '2026-01-31',
      section: 'Datos de la entidad'
    }
  ],
  field_mappings: [],
  unmapped_fields: [],
  kind_id: null,
  reporter_path: 'nit_entidad',
  reporter_name_path: null,
  period_path: null
}

const API = 'http://localhost:8000'

function corsHeaders(origin: string) {
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-credentials': 'true',
    'access-control-allow-headers': 'content-type',
    'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS'
  }
}

/** Every request the edit screen makes, plus the proposals it asks for. */
async function stubServer(page: Page, baseURL: string, proposals: string[]) {
  const headers = corsHeaders(new URL(baseURL).origin)
  const json = (body: unknown) => async (route: Route) => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    return route.fulfill({ json: body, headers })
  }

  await page.route(`${API}/auth/google/me`, json({ email: 'p@example.com', name: 'P', picture: null }))
  await page.route(`${API}/reconciliation/kinds`, json([]))
  await page.route(`${API}/reconciliation/kinds/**`, json(null))
  await page.route(`${API}/documents/doc-1`, json(SAMPLE))
  await page.route(`${API}/documents?**`, json([SAMPLE]))
  await page.route(`${API}/document-types?**`, json([TYPE]))
  await page.route(`${API}/document-types/proposals`, async (route) => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    proposals.push(route.request().postData() ?? '')
    return route.fulfill({ json: PROPOSAL, headers })
  })
  await page.route(`${API}/document-types/type-1`, json(TYPE))
}

async function regenerate(page: Page) {
  await page.goto('/document-types/type-1')
  await page.waitForLoadState('networkidle')
  await page.getByTestId('regenerate-guidance').fill('Falta la fecha de expedición.')
  await page.getByRole('button', { name: 'Regenerar con estas indicaciones' }).click()
  await expect(page.getByTestId('regenerate-preview')).toBeVisible()
}

test.describe('Regenerar un tipo de documento', () => {
  test('names the fields that would stop being extracted', async ({ page, baseURL }) => {
    // A count is not an answer to "which ones", and every field dropped takes
    // its concept mapping with it.
    await stubServer(page, baseURL!, [])
    await regenerate(page)

    const removed = page.getByTestId('regenerate-removed')
    await expect(removed).toContainText('Base gravable del GMF')
    await expect(removed).toContainText('base_gravable')
  })

  test('badges the dropped field in the block it belongs to, ready to be ticked back', async ({
    page,
    baseURL
  }) => {
    await stubServer(page, baseURL!, [])
    await regenerate(page)

    const row = page.getByTestId('field-row-base_gravable')
    await expect(row).toContainText('Se dejaría de extraer')
    await expect(row.getByRole('checkbox')).not.toBeChecked()
  })

  test('hides what the type extracts today while a reading is being iterated on', async ({
    page,
    baseURL
  }) => {
    // Two field lists on one screen read as one list of contradictions, and
    // the stored one carries a Save that writes a different decision.
    await stubServer(page, baseURL!, [])
    await page.goto('/document-types/type-1')
    await page.waitForLoadState('networkidle')
    await expect(page.getByTestId('field-rows')).toBeVisible()
    await expect(page.getByTestId('save-document-type')).toBeVisible()

    await page.getByRole('button', { name: 'Regenerar con estas indicaciones' }).click()
    await expect(page.getByTestId('regenerate-preview')).toBeVisible()

    await expect(page.getByTestId('field-rows')).toBeHidden()
    await expect(page.getByTestId('save-document-type')).toBeHidden()
  })

  test('brings the stored configuration back when the reading is discarded', async ({
    page,
    baseURL
  }) => {
    await stubServer(page, baseURL!, [])
    await regenerate(page)

    await page.getByRole('button', { name: 'Descartar' }).click()

    await expect(page.getByTestId('field-rows')).toBeVisible()
    await expect(page.getByTestId('regenerate-preview')).toBeHidden()
  })

  test('asks for the next instruction beside the buttons, with the answer in hand', async ({
    page,
    baseURL
  }) => {
    // The instruction being written is about the list just read; a box at the
    // top of the screen describes fields the writer can no longer see.
    const proposals: string[] = []
    await stubServer(page, baseURL!, proposals)
    await regenerate(page)

    await page.getByTestId('field-row-fecha_expedicion').getByRole('checkbox').check()
    await page.getByTestId('reread-guidance').fill('La fecha va con día, mes y año por separado.')
    await page.getByTestId('reread-type').click()

    await expect.poll(() => proposals.length).toBe(2)
    const body = proposals[1]!
    expect(body).toContain('La fecha va con día, mes y año por separado.')
    const selection = JSON.parse(/name="selection"\r\n\r\n(.*?)\r\n/s.exec(body)![1]!)
    expect(selection.kept.map((field: { path: string }) => field.path)).toContain(
      'fecha_expedicion'
    )
  })

  test('shows a proposed amount the way the certificate prints one', async ({ page, baseURL }) => {
    await stubServer(page, baseURL!, [])
    await regenerate(page)

    await expect(page.getByTestId('field-row-gmf')).toContainText('$ 512.561,52')
  })

  test('sends what the reader said about a whole block of the page', async ({ page, baseURL }) => {
    // The correction that matters most on a certificate — what a table
    // actually is — governs every field under one heading, so it is said
    // against the heading rather than repeated on each row.
    const proposals: string[] = []
    await stubServer(page, baseURL!, proposals)
    await regenerate(page)

    await page.getByTestId('section-annotate-Gravamen a los movimientos financieros').click()
    await page
      .getByTestId('section-note-Gravamen a los movimientos financieros')
      .fill('Son mensuales, no acumulados.')
    await page.getByTestId('reread-type').click()

    await expect.poll(() => proposals.length).toBe(2)
    const selection = JSON.parse(/name="selection"\r\n\r\n(.*?)\r\n/s.exec(proposals[1]!)![1]!)
    expect(selection.sections).toContainEqual({
      section: 'Gravamen a los movimientos financieros',
      note: 'Son mensuales, no acumulados.'
    })
  })

  test('reads the stored fields as money too, not only the proposed ones', async ({
    page,
    baseURL
  }) => {
    // The list of what the type extracts today is where the accountant checks
    // a figure against the paper most often, and it was the one showing the
    // raw `2241275.17`.
    await stubServer(page, baseURL!, [])
    await page.goto('/document-types/type-1')
    await page.waitForLoadState('networkidle')

    await expect(page.getByTestId('field-rows')).toContainText('$ 2.241.275,17')
  })

  test('names the stored fields as kept on the very first reading', async ({ page, baseURL }) => {
    // The press that has no round behind it is the one that used to send
    // nothing, leaving a prose instruction as the only thing asking the model
    // not to drop a field the type already declares.
    const proposals: string[] = []
    await stubServer(page, baseURL!, proposals)
    await regenerate(page)

    await expect.poll(() => proposals.length).toBe(1)
    const selection = JSON.parse(/name="selection"\r\n\r\n(.*?)\r\n/s.exec(proposals[0]!)![1]!)
    expect(selection.kept.map((field: { path: string }) => field.path)).toEqual([
      'nit_entidad',
      'gmf',
      'base_gravable'
    ])
    expect(selection.dropped).toEqual([])
  })
})
