import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpConceptMappingRepository } from '~/infrastructure/http/http-concept-mapping-repository'

const KIND_DTO = {
  id: 'exogena_dian',
  label: 'Exógena DIAN',
  period_granularity: 'year',
  spine_concepts: [
    {
      id: 'dian:saldo-cuentas-bancarias',
      label: 'Saldo de cuentas bancarias',
      role: 'spine',
      description: ''
    }
  ],
  evidence_concepts: [
    {
      id: 'bank:cert_saldo',
      label: 'Saldo certificado',
      role: 'evidence',
      description: 'Saldo a 31 de diciembre'
    }
  ]
}

const MAPPING_DTO = {
  document_type_id: 'dt-1',
  kind_id: 'exogena_dian',
  entries: [
    {
      field_path: 'accounts[].balance',
      concept_id: 'bank:cert_saldo',
      account_path: 'accounts[].number',
      sign: -1,
      spine_concept_id: 'dian:saldo-cuentas-bancarias',
      per_account: true
    }
  ],
  reporter_path: 'bank_tax_id',
  reporter_name_path: 'bank_name',
  period_path: 'year'
}

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(handler: (path: string, options?: Record<string, unknown>) => unknown) {
  const fetcher = vi.fn(handler)
  vi.stubGlobal('$fetch', fetcher)
  return fetcher
}

describe('HttpConceptMappingRepository', () => {
  it('maps a kind into the vocabulary the configuration screen offers', async () => {
    stubFetch(() => [KIND_DTO])

    const [kind] = await new HttpConceptMappingRepository('http://api').listKinds()

    expect(kind!.periodGranularity).toBe('year')
    expect(kind!.evidenceConcepts[0]!.label).toBe('Saldo certificado')
  })

  it('maps a stored mapping into the shape the app reads', async () => {
    stubFetch(() => MAPPING_DTO)

    const mapping = await new HttpConceptMappingRepository('http://api').get(
      'exogena_dian',
      'dt-1'
    )

    expect(mapping!.reporterPath).toBe('bank_tax_id')
    expect(mapping!.entries[0]).toEqual({
      fieldPath: 'accounts[].balance',
      conceptId: 'bank:cert_saldo',
      accountPath: 'accounts[].number',
      sign: -1,
      spineConceptId: 'dian:saldo-cuentas-bancarias',
      perAccount: true,
      rowLabelPath: null,
      rowLabel: null
    })
  })

  it('reads a missing mapping as none rather than as a failure', async () => {
    stubFetch(() => {
      throw { statusCode: 404 }
    })

    const mapping = await new HttpConceptMappingRepository('http://api').get(
      'exogena_dian',
      'dt-1'
    )

    expect(mapping).toBeNull()
  })

  it('lets any other failure surface', async () => {
    stubFetch(() => {
      throw { statusCode: 500 }
    })

    await expect(
      new HttpConceptMappingRepository('http://api').get('exogena_dian', 'dt-1')
    ).rejects.toBeTruthy()
  })

  it('puts the mapping in the server\'s casing, session cookie included', async () => {
    const fetcher = stubFetch(() => MAPPING_DTO)

    await new HttpConceptMappingRepository('http://api').save('exogena_dian', 'dt-1', {
      entries: [
        {
          fieldPath: 'accounts[].balance',
          conceptId: 'bank:cert_saldo',
          accountPath: null,
          sign: 1,
          spineConceptId: 'dian:saldo-cuentas-bancarias',
          perAccount: false,
          rowLabelPath: null,
          rowLabel: null
        }
      ],
      reporterPath: 'bank_tax_id',
      reporterNamePath: null,
      periodPath: null,
      reporterTaxId: null,
      reporterName: null,
      period: null
    })

    const [path, options] = fetcher.mock.calls[0]!
    expect(path).toBe('/reconciliation/kinds/exogena_dian/document-types/dt-1/mapping')
    expect(options).toMatchObject({ method: 'PUT', credentials: 'include' })
    expect(options!.body).toEqual({
      entries: [
        {
          field_path: 'accounts[].balance',
          concept_id: 'bank:cert_saldo',
          account_path: null,
          sign: 1,
          spine_concept_id: 'dian:saldo-cuentas-bancarias',
          per_account: false,
          row_label_path: null,
          row_label: null
        }
      ],
      reporter_path: 'bank_tax_id',
      reporter_name_path: null,
      period_path: null,
      reporter_tax_id: null,
      reporter_name: null,
      period: null
    })
  })

  it('sends the values a type declares for the papers that never state them', async () => {
    const fetcher = stubFetch(() => MAPPING_DTO)

    await new HttpConceptMappingRepository('http://api').save('exogena_dian', 'dt-1', {
      entries: [],
      reporterPath: null,
      reporterNamePath: null,
      periodPath: null,
      reporterTaxId: '890903938',
      reporterName: 'JFK Cooperativa Financiera',
      period: '2025'
    })

    expect(fetcher.mock.calls[0]![1]!.body).toMatchObject({
      reporter_tax_id: '890903938',
      reporter_name: 'JFK Cooperativa Financiera',
      period: '2025'
    })
  })

  it('reads an entry stored before the spine line existed as answering none', async () => {
    stubFetch(() => ({
      ...MAPPING_DTO,
      entries: [
        {
          field_path: 'gmf',
          concept_id: 'bank:cert_gmf_valor',
          account_path: null,
          sign: 1
        }
      ]
    }))

    const mapping = await new HttpConceptMappingRepository('http://api').get(
      'exogena_dian',
      'dt-1'
    )

    // Not a failure: that mapping did feed a fact, it simply had nothing to be
    // compared against, and inventing a line here would fabricate a comparison.
    expect(mapping!.entries[0]).toMatchObject({ spineConceptId: null, perAccount: false })
  })
})

describe('HttpConceptMappingRepository, a table answered row by row', () => {
  it('carries which row of the table each entry answers, both ways', async () => {
    const dto = {
      document_type_id: 'dt-1',
      kind_id: 'exogena_dian',
      reporter_path: 'nit',
      reporter_name_path: null,
      period_path: null,
      entries: [
        {
          field_path: 'ingresos[].valor',
          concept_id: 'payroll:cert_pagos_salarios',
          account_path: null,
          sign: 1,
          spine_concept_id: 'dian:pagos-salarios',
          per_account: false,
          row_label_path: 'ingresos[].concepto',
          row_label: 'Pagos por salarios'
        }
      ]
    }
    stubFetch(() => dto)

    const mapping = await new HttpConceptMappingRepository('http://api').get(
      'exogena_dian',
      'dt-1'
    )

    expect(mapping!.entries[0]!.rowLabelPath).toBe('ingresos[].concepto')
    expect(mapping!.entries[0]!.rowLabel).toBe('Pagos por salarios')
  })

  it('reads half a pair as no pair, since a lone path claims every row', async () => {
    const dto = {
      document_type_id: 'dt-1',
      kind_id: 'exogena_dian',
      reporter_path: 'nit',
      reporter_name_path: null,
      period_path: null,
      entries: [
        {
          field_path: 'ingresos[].valor',
          concept_id: 'payroll:cert_pagos_salarios',
          account_path: null,
          sign: 1,
          row_label_path: 'ingresos[].concepto'
        }
      ]
    }
    stubFetch(() => dto)

    const mapping = await new HttpConceptMappingRepository('http://api').get(
      'exogena_dian',
      'dt-1'
    )

    expect(mapping!.entries[0]!.rowLabelPath).toBeNull()
    expect(mapping!.entries[0]!.rowLabel).toBeNull()
  })
})
