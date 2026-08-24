import { describe, expect, it } from 'vitest'
import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { DocumentListFilter, DocumentRepository,
  ClientDocumentsImport
} from '~/application/ports/document-repository'
import { GetDocument } from '~/application/use-cases/get-document'

class FakeDocumentRepository implements DocumentRepository {
  constructor(
    private readonly document: ClientDocument | null = null,
    private readonly extractedData: ExtractedData | null = null
  ) {}

  getById(_id: string): Promise<ClientDocument> {
    if (!this.document) {
      return Promise.reject(new Error('Document not found'))
    }
    return Promise.resolve(this.document)
  }

  getExtractedData(_id: string): Promise<ExtractedData | null> {
    return Promise.resolve(this.extractedData)
  }

  listByClient(_clientId: string): Promise<ClientDocument[]> {
    throw new Error('not implemented')
  }

  list(_filter?: DocumentListFilter): Promise<ClientDocument[]> {
    throw new Error('not implemented')
  }

  importForClient(_clientId: string): Promise<ClientDocumentsImport> {
    throw new Error('not implemented')
  }
}

describe('GetDocument', () => {
  it('returns the document from the repository', async () => {
    const document: ClientDocument = {
      id: '1',
      clientId: 'client-1',
      documentTypeId: 'type-1',
      driveFileId: 'drive-1',
      fileName: 'statement.pdf',
      mimeType: 'application/pdf',
      status: 'processed',
      error: null,
      createdAt: '2026-01-01',
      processedAt: '2026-01-01'
    }
    const useCase = new GetDocument(new FakeDocumentRepository(document))

    await expect(useCase.execute('1')).resolves.toEqual(document)
  })

  it('propagates the repository error when the document does not exist', async () => {
    const useCase = new GetDocument(new FakeDocumentRepository(null))

    await expect(useCase.execute('missing')).rejects.toThrow('Document not found')
  })
})
