import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpDocumentTypeRepository } from '~/infrastructure/http/http-document-type-repository'

const DOCUMENT_TYPE_DTO = {
  id: 'dt-1',
  name: 'Certificado Bancolombia',
  description: 'Certificado anual',
  extraction_prompt: 'Extract the certificate fields',
  extraction_schema: { type: 'object', properties: { balance: { type: 'string' } } },
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  fields: [
    {
      path: 'cuentas[].saldo',
      label: 'Saldo a 31 de diciembre',
      role: 'amount',
      section: 'Cuentas de ahorro'
    },
    { path: 'pie_de_pagina' }
  ],
  mapping_changes: [
    {
      kind_id: 'exogena_dian',
      change: 'entry_dropped',
      path: 'gmf',
      field_path: 'gmf',
      concept_id: 'bank:cert_gmf_valor',
      reason: 'the schema no longer declares this field'
    }
  ]
}

/**
 * What POST /document-types actually answers.
 *
 * Deliberately separate from DOCUMENT_TYPE_DTO: creation reports
 * `unmapped_fields` and carries no `mapping_changes`, and a fixture that
 * invented the latter is what let the adapter read the wrong key.
 */
const CREATED_DTO = {
  id: 'dt-1',
  name: 'Certificado GMF',
  description: '',
  extraction_prompt: '',
  extraction_schema: {},
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  fields: [],
  kind_id: 'exogena_dian',
  field_mappings: [],
  unmapped_fields: [
    {
      field_path: 'gmf',
      reason: 'the document does not say who reports these amounts'
    }
  ]
}

const PROPOSAL_DTO = {
  extraction_prompt: 'Extrae los campos del certificado',
  extraction_schema: { type: 'object', properties: { gmf: { type: 'array' } } },
  fields: [
    {
      path: 'gmf[].valor',
      label: 'Valor GMF',
      role: 'amount',
      sample_value: '512.561,52',
      section: 'Gravamen a los movimientos financieros'
    },
    { path: 'notas', role: 'nonsense' }
  ],
  field_mappings: [
    { field_path: 'gmf[].valor', concept_id: 'bank:gmf', account_path: null, sign: -1 }
  ],
  unmapped_fields: [{ field_path: 'notas', reason: 'not an amount' }],
  kind_id: 'exogena_dian',
  reporter_path: 'agente_retenedor.nit',
  reporter_name_path: 'agente_retenedor.nombre',
  period_path: 'anio_gravable'
}

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(handler: (path: string, options?: Record<string, unknown>) => unknown) {
  const fetcher = vi.fn(handler)
  vi.stubGlobal('$fetch', fetcher)
  return fetcher
}

const sampleFile = () => new File(['sample'], 'sample.pdf', { type: 'application/pdf' })

describe('HttpDocumentTypeRepository.propose', () => {
  it('maps a proposal into the shape the screen reads', async () => {
    stubFetch(() => PROPOSAL_DTO)

    const proposal = await new HttpDocumentTypeRepository('http://api').propose({
      name: 'Certificado GMF',
      sampleFile: sampleFile()
    })

    expect(proposal.fields[0]).toEqual({
      path: 'gmf[].valor',
      label: 'Valor GMF',
      role: 'amount',
      sampleValue: '512.561,52',
      section: 'Gravamen a los movimientos financieros'
    })
    expect(proposal.fieldMappings).toEqual([
      { fieldPath: 'gmf[].valor', conceptId: 'bank:gmf', accountPath: null, sign: -1 }
    ])
    expect(proposal.reporterPath).toBe('agente_retenedor.nit')
    expect(proposal.unmappedFields).toEqual([{ fieldPath: 'notas', reason: 'not an amount' }])
  })

  it('reads an unknown role as context, so the field is not selected by default', async () => {
    stubFetch(() => PROPOSAL_DTO)

    const proposal = await new HttpDocumentTypeRepository('http://api').propose({
      name: 'Certificado GMF',
      sampleFile: sampleFile()
    })

    expect(proposal.fields[1]).toMatchObject({ path: 'notas', role: 'context' })
  })

  it('posts the sample as multipart to the proposals endpoint', async () => {
    const fetcher = stubFetch(() => PROPOSAL_DTO)

    await new HttpDocumentTypeRepository('http://api').propose({
      name: 'Certificado GMF',
      sampleFile: sampleFile(),
      kindId: 'exogena_dian'
    })

    const [path, options] = fetcher.mock.calls[0]!
    expect(path).toBe('/document-types/proposals')
    expect(options).toMatchObject({ method: 'POST', credentials: 'include' })
    const body = options!.body as FormData
    expect(body.get('name')).toBe('Certificado GMF')
    expect(body.get('kind_id')).toBe('exogena_dian')
    expect(body.get('sample_file')).toBeInstanceOf(File)
  })
})

describe('HttpDocumentTypeRepository.create', () => {
  it('sends the trimmed type as JSON, with no file', async () => {
    const fetcher = stubFetch(() => DOCUMENT_TYPE_DTO)

    await new HttpDocumentTypeRepository('http://api').create({
      name: 'Certificado GMF',
      description: 'Certificado de GMF',
      extractionPrompt: 'Extrae los campos del certificado',
      extractionSchema: { type: 'object', properties: {} },
      fieldMappings: [
        { fieldPath: 'gmf[].valor', conceptId: 'bank:gmf', accountPath: null, sign: -1 }
      ],
      fields: [
        {
          path: 'gmf[].valor',
          label: 'Valor GMF',
          role: 'amount',
          section: 'Gravamen a los movimientos financieros'
        }
      ],
      reporterPath: 'agente_retenedor.nit',
      reporterNamePath: null,
      periodPath: 'anio_gravable',
      taxYears: [2024, 2025],
      kindId: 'exogena_dian',
      sampleDocumentId: 'doc-1'
    })

    expect(fetcher).toHaveBeenCalledWith('/document-types', {
      baseURL: 'http://api',
      method: 'POST',
      credentials: 'include',
      body: {
        name: 'Certificado GMF',
        description: 'Certificado de GMF',
        extraction_prompt: 'Extrae los campos del certificado',
        extraction_schema: { type: 'object', properties: {} },
        field_mappings: [
          { field_path: 'gmf[].valor', concept_id: 'bank:gmf', account_path: null, sign: -1 }
        ],
        reporter_path: 'agente_retenedor.nit',
        reporter_name_path: null,
        period_path: 'anio_gravable',
        tax_years: [2024, 2025],
        fields: [
          {
            path: 'gmf[].valor',
            label: 'Valor GMF',
            role: 'amount',
            section: 'Gravamen a los movimientos financieros'
          }
        ],
        kind_id: 'exogena_dian',
        sample_document_id: 'doc-1'
      }
    })
  })

  it('reads back the fields that will be extracted but never reconciled', async () => {
    // The failure this guards: the server saves the type and discards every
    // mapping for want of a reporting party, and the screen calls it success.
    stubFetch(() => CREATED_DTO)

    const created = await new HttpDocumentTypeRepository('http://api').create({
      name: 'Certificado GMF',
      description: '',
      extractionPrompt: '',
      extractionSchema: {},
      fieldMappings: [],
      fields: [],
      reporterPath: null,
      reporterNamePath: null,
      periodPath: null,
      taxYears: [],
      kindId: null,
      sampleDocumentId: null
    })

    expect(created.documentType.id).toBe('dt-1')
    expect(created.unmappedFields).toEqual([
      { fieldPath: 'gmf', reason: 'the document does not say who reports these amounts' }
    ])
  })
})

describe('HttpDocumentTypeRepository field descriptions', () => {
  it('reads the label and section the document uses', async () => {
    stubFetch(() => [DOCUMENT_TYPE_DTO])

    const [documentType] = await new HttpDocumentTypeRepository('http://api').list()

    expect(documentType!.fields[0]).toEqual({
      path: 'cuentas[].saldo',
      label: 'Saldo a 31 de diciembre',
      role: 'amount',
      section: 'Cuentas de ahorro'
    })
  })

  it('falls back to the path for a field stored before descriptions existed', async () => {
    stubFetch(() => [DOCUMENT_TYPE_DTO])

    const [documentType] = await new HttpDocumentTypeRepository('http://api').list()

    expect(documentType!.fields[1]).toEqual({
      path: 'pie_de_pagina',
      label: 'pie_de_pagina',
      role: 'context',
      section: ''
    })
  })
})

describe('HttpDocumentTypeRepository.update', () => {
  it('patches the type with only the fields that changed, in the server\'s casing', async () => {
    const fetcher = stubFetch(() => DOCUMENT_TYPE_DTO)

    await new HttpDocumentTypeRepository('http://api').update('dt-1', {
      extractionSchema: { type: 'object', properties: {} }
    })

    const [path, options] = fetcher.mock.calls[0]!
    expect(path).toBe('/document-types/dt-1')
    expect(options).toMatchObject({ method: 'PATCH', credentials: 'include' })
    expect(options!.body).toEqual({ extraction_schema: { type: 'object', properties: {} } })
  })

  it('reports the mapping the server dropped as a consequence of the edit', async () => {
    stubFetch(() => DOCUMENT_TYPE_DTO)

    const { documentType, mappingChanges } = await new HttpDocumentTypeRepository(
      'http://api'
    ).update('dt-1', { extractionSchema: { type: 'object', properties: {} } })

    expect(documentType.extractionPrompt).toBe('Extract the certificate fields')
    expect(mappingChanges).toEqual([
      {
        kindId: 'exogena_dian',
        change: 'entry_dropped',
        path: 'gmf',
        fieldPath: 'gmf',
        conceptId: 'bank:cert_gmf_valor',
        reason: 'the schema no longer declares this field'
      }
    ])
  })

  it('reports no mapping changes when the response carries none', async () => {
    stubFetch(() => ({ ...DOCUMENT_TYPE_DTO, mapping_changes: undefined }))

    const { mappingChanges } = await new HttpDocumentTypeRepository('http://api').update('dt-1', {
      name: 'Otro nombre'
    })

    expect(mappingChanges).toEqual([])
  })
})
