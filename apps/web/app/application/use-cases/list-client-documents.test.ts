import { describe, expect, it } from 'vitest'
import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { DocumentRepository } from '~/application/ports/document-repository'
import { ListClientDocuments } from '~/application/use-cases/list-client-documents'

class FakeDocumentRepository implements DocumentRepository {
  constructor(private readonly documents: ClientDocument[]) {}

  getById(_id: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  getExtractedData(_id: string): Promise<ExtractedData | null> {
    throw new Error('not implemented')
  }

  listByClient(clientId: string): Promise<ClientDocument[]> {
    return Promise.resolve(this.documents.filter(d => d.clientId === clientId))
  }
}

describe('ListClientDocuments', () => {
  it('returns the documents for the given client', async () => {
    const documents: ClientDocument[] = [
      {
        id: 'doc-1',
        clientId: 'client-1',
        documentTypeId: null,
        driveFileId: 'drive-1',
        fileName: 'statement.pdf',
        mimeType: 'application/pdf',
        status: 'pending',
        error: null,
        createdAt: '2026-01-01T10:00:00Z'
      }
    ]
    const useCase = new ListClientDocuments(new FakeDocumentRepository(documents))

    await expect(useCase.execute('client-1')).resolves.toEqual(documents)
  })
})
