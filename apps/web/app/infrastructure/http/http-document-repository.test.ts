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

describe('HttpDocumentRepository.importForClient', () => {
  const IMPORT_DTO = {
    imported: [
      {
        id: 'd1',
        client_id: 'c1',
        document_type_id: 't1',
        drive_file_id: 'drive-1',
        file_name: 'cert.pdf',
        mime_type: 'application/pdf',
        status: 'processed',
        error: null,
        created_at: '2026-08-24T00:00:00Z',
        processed_at: '2026-08-24T00:01:00Z'
      }
    ],
    failed: [],
    unreadable: ['drive-2'],
    skipped: 3
  }

  it('posts to the client import endpoint with the session cookie', async () => {
    const fetcher = vi.fn(() => IMPORT_DTO)
    vi.stubGlobal('$fetch', fetcher)

    const result = await new HttpDocumentRepository('http://api').importForClient('c1')

    expect(fetcher).toHaveBeenCalledWith(
      '/clients/c1/documents/import',
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )
    expect(result.imported[0]!.fileName).toBe('cert.pdf')
    expect(result.unreadable).toEqual(['drive-2'])
    expect(result.skipped).toBe(3)
    vi.unstubAllGlobals()
  })
})
