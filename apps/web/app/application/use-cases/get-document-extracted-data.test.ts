import { describe, expect, it } from 'vitest'
import type { DocumentSource } from '~/domain/entities/document-source'
import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { DocumentListFilter, DocumentRepository,
  ClientDocumentsImport
} from '~/application/ports/document-repository'
import { GetDocumentExtractedData } from '~/application/use-cases/get-document-extracted-data'

class FakeDocumentRepository implements DocumentRepository {
  constructor(private readonly extractedData: ExtractedData | null) {}

  getById(_id: string): Promise<ClientDocument> {
    throw new Error('not implemented')
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

  listSources(): Promise<DocumentSource[]> {
    throw new Error('not implemented')
  }

  recognizeSource(_id: string, _sourceId: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  approve(_id: string, _approvedBy?: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }
}

describe('GetDocumentExtractedData', () => {
  it('returns the extracted data from the repository', async () => {
    const extractedData: ExtractedData = {
      id: '1',
      documentId: 'doc-1',
      fields: { total: 100 },
      confidence: 0.95,
      createdAt: '2026-01-01'
    }
    const useCase = new GetDocumentExtractedData(new FakeDocumentRepository(extractedData))

    await expect(useCase.execute('doc-1')).resolves.toEqual(extractedData)
  })

  it('returns null when the extraction has not been generated yet', async () => {
    const useCase = new GetDocumentExtractedData(new FakeDocumentRepository(null))

    await expect(useCase.execute('doc-1')).resolves.toBeNull()
  })
})
