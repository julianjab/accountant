import { describe, expect, it } from 'vitest'
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentSource } from '~/domain/entities/document-source'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { ClientDocumentsImport, DocumentListFilter, DocumentRepository } from '~/application/ports/document-repository'
import { ListDocumentSources } from '~/application/use-cases/list-document-sources'

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

const SOURCES: DocumentSource[] = [
  { id: 'exogena_report', label: 'Reporte de información exógena (DIAN)', mediaTypes: [XLSX] },
  { id: 'bank_ledger', label: 'Libro auxiliar', mediaTypes: ['text/csv'] }
]

class FakeDocumentRepository implements DocumentRepository {
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

  importForClient(_clientId: string): Promise<ClientDocumentsImport> {
    throw new Error('not implemented')
  }

  listSources(): Promise<DocumentSource[]> {
    return Promise.resolve(SOURCES)
  }

  recognizeSource(_id: string, _sourceId: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  approve(_id: string, _approvedBy?: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  reopen(_id: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }
}

describe('ListDocumentSources', () => {
  it('offers only the sources whose parser accepts the file', async () => {
    const useCase = new ListDocumentSources(new FakeDocumentRepository())

    await expect(useCase.execute(XLSX)).resolves.toEqual([SOURCES[0]])
  })

  it('offers nothing when no parser reads this kind of file', async () => {
    const useCase = new ListDocumentSources(new FakeDocumentRepository())

    await expect(useCase.execute('application/pdf')).resolves.toEqual([])
  })

  it('offers all of them when no media type narrows the choice', async () => {
    const useCase = new ListDocumentSources(new FakeDocumentRepository())

    await expect(useCase.execute()).resolves.toEqual(SOURCES)
  })
})
