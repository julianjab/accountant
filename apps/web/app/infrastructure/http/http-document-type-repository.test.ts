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

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(handler: (path: string, options?: Record<string, unknown>) => unknown) {
  const fetcher = vi.fn(handler)
  vi.stubGlobal('$fetch', fetcher)
  return fetcher
}

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
