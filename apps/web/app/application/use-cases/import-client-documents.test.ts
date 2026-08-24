import { describe, expect, it } from 'vitest'
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type {
  ClientDocumentsImport,
  DocumentListFilter,
  DocumentRepository
} from '~/application/ports/document-repository'
import { ImportClientDocuments } from '~/application/use-cases/import-client-documents'

function documentOf(id: string, status: DocumentStatus = 'processed'): ClientDocument {
  return {
    id,
    clientId: 'c1',
    documentTypeId: null,
    driveFileId: `drive-${id}`,
    fileName: `${id}.pdf`,
    mimeType: 'application/pdf',
    status,
    error: null,
    createdAt: '2026-08-24T00:00:00Z',
    processedAt: null,
    sourceId: null
  }
}

class FakeDocumentRepository implements DocumentRepository {
  readonly imported: string[] = []

  constructor(private readonly result: ClientDocumentsImport) {}

  getById(_id: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  getExtractedData(_id: string): Promise<ExtractedData | null> {
    throw new Error('not implemented')
  }

  listByClient(_clientId: string): Promise<ClientDocument[]> {
    throw new Error('not implemented')
  }

  list(_filter?: DocumentListFilter): Promise<ClientDocument[]> {
    throw new Error('not implemented')
  }

  importForClient(clientId: string): Promise<ClientDocumentsImport> {
    this.imported.push(clientId)
    return Promise.resolve(this.result)
  }

  approve(_id: string, _approvedBy?: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }
}

describe('ImportClientDocuments', () => {
  it('asks for the client folder to be processed', async () => {
    const repository = new FakeDocumentRepository({
      imported: [documentOf('d1')],
      failed: [],
      unreadable: [],
      skipped: 2
    })

    const result = await new ImportClientDocuments(repository).execute('c1')

    expect(repository.imported).toEqual(['c1'])
    expect(result.imported).toHaveLength(1)
    expect(result.skipped).toBe(2)
  })

  it('keeps what went wrong separate from what worked', async () => {
    // A folder of ten answering "imported 3" with nothing else would give the
    // caller no way to learn the other seven were never looked at.
    const repository = new FakeDocumentRepository({
      imported: [documentOf('d1')],
      failed: [documentOf('d2', 'failed')],
      unreadable: ['drive-d3'],
      skipped: 0
    })

    const result = await new ImportClientDocuments(repository).execute('c1')

    expect(result.failed.map(d => d.id)).toEqual(['d2'])
    expect(result.unreadable).toEqual(['drive-d3'])
  })
})
