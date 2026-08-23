import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpDocumentRepository } from '~/infrastructure/http/http-document-repository'

describe('HttpDocumentRepository', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('maps the document DTO to a ClientDocument', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      id: 'doc-1',
      client_id: 'client-1',
      document_type_id: 'type-1',
      drive_file_id: 'drive-1',
      file_name: 'statement.pdf',
      mime_type: 'application/pdf',
      status: 'processed',
      error: null,
      created_at: '2026-01-01'
    })
    vi.stubGlobal('$fetch', fetchMock)

    const repository = new HttpDocumentRepository('http://localhost:8000')
    const result = await repository.getById('doc-1')

    expect(result).toEqual({
      id: 'doc-1',
      clientId: 'client-1',
      documentTypeId: 'type-1',
      driveFileId: 'drive-1',
      fileName: 'statement.pdf',
      mimeType: 'application/pdf',
      status: 'processed',
      error: null,
      createdAt: '2026-01-01'
    })
    expect(fetchMock).toHaveBeenCalledWith('/documents/doc-1', {
      baseURL: 'http://localhost:8000',
      credentials: 'include'
    })
  })

  it('propagates a 404 error when the document does not exist', async () => {
    vi.stubGlobal('$fetch', vi.fn().mockRejectedValue({ statusCode: 404 }))

    const repository = new HttpDocumentRepository('http://localhost:8000')

    await expect(repository.getById('missing')).rejects.toBeTruthy()
  })

  it('maps the extracted data DTO to an ExtractedData', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      id: 'extracted-1',
      document_id: 'doc-1',
      fields: { total: 100 },
      confidence: 0.95,
      created_at: '2026-01-01'
    })
    vi.stubGlobal('$fetch', fetchMock)

    const repository = new HttpDocumentRepository('http://localhost:8000')
    const result = await repository.getExtractedData('doc-1')

    expect(result).toEqual({
      id: 'extracted-1',
      documentId: 'doc-1',
      fields: { total: 100 },
      confidence: 0.95,
      createdAt: '2026-01-01'
    })
  })

  it('returns null when the extracted data endpoint responds 404', async () => {
    vi.stubGlobal('$fetch', vi.fn().mockRejectedValue({ statusCode: 404 }))

    const repository = new HttpDocumentRepository('http://localhost:8000')

    await expect(repository.getExtractedData('doc-1')).resolves.toBeNull()
  })

  it('propagates non-404 errors when fetching extracted data', async () => {
    vi.stubGlobal('$fetch', vi.fn().mockRejectedValue({ statusCode: 500 }))

    const repository = new HttpDocumentRepository('http://localhost:8000')

    await expect(repository.getExtractedData('doc-1')).rejects.toBeTruthy()
  })
})
