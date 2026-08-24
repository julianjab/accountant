import { describe, expect, it } from 'vitest'
import type { Client } from '~/domain/entities/client'
import type { DocumentSource } from '~/domain/entities/document-source'
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentType, DocumentTypeCreation, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type { ClientRepository, ImportSummary, RegisterClientInput } from '~/application/ports/client-repository'
import type { DocumentListFilter, DocumentRepository,
  ClientDocumentsImport
} from '~/application/ports/document-repository'
import type {
  CreateDocumentTypeInput,
  ProposeDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { ListInbox } from '~/application/use-cases/list-inbox'

const SOURCES: DocumentSource[] = [
  { id: 'exogena_report', label: 'Reporte de información exógena (DIAN)', mediaTypes: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'] }
]

class FakeClientRepository implements ClientRepository {
  constructor(private readonly clients: Client[]) {}

  list(): Promise<Client[]> {
    return Promise.resolve(this.clients)
  }

  get(id: string): Promise<Client | null> {
    return Promise.resolve(this.clients.find(c => c.id === id) ?? null)
  }

  register(_input: RegisterClientInput): Promise<Client> {
    throw new Error('not implemented')
  }

  importFromDrive(): Promise<ImportSummary> {
    throw new Error('not implemented')
  }
}

class FakeDocumentRepository implements DocumentRepository {
  constructor(private readonly documents: ClientDocument[]) {}

  getById(_id: string): Promise<ClientDocument> {
    throw new Error('not implemented')
  }

  getExtractedData(_id: string): Promise<null> {
    throw new Error('not implemented')
  }

  listByClient(_clientId: string): Promise<ClientDocument[]> {
    throw new Error('not implemented')
  }

  list(_filter?: DocumentListFilter): Promise<ClientDocument[]> {
    return Promise.resolve(this.documents)
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

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly types: DocumentType[]) {}

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    return Promise.resolve(this.types)
  }

  propose(_input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    throw new Error('not implemented')
  }

  create(_input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    throw new Error('not implemented')
  }

  remove(_id: string): Promise<void> {
    return Promise.resolve()
  }

  update(_id: string, _changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    throw new Error('not implemented')
  }
}

function client(overrides: Partial<Client>): Client {
  return {
    id: 'c1',
    name: 'Jane Doe',
    taxId: '123',
    email: null,
    createdAt: '2026-01-01',
    driveFolderId: null,
    driveFolderUrl: null,
    spreadsheetUrl: null,
    ...overrides
  }
}

function document(overrides: Partial<ClientDocument>): ClientDocument {
  return {
    id: 'd1',
    clientId: 'c1',
    documentTypeId: null,
    driveFileId: 'drive-1',
    fileName: 'file.pdf',
    mimeType: 'application/pdf',
    status: 'pending',
    error: null,
    createdAt: '2026-08-22T10:00:00.000Z',
    processedAt: null,
    sourceId: null,
    ...overrides
  }
}

describe('ListInbox', () => {
  it('groups documents by client, sorted by client name then id', async () => {
    const clients = [client({ id: 'c2', name: 'Beta' }), client({ id: 'c1', name: 'Alpha' })]
    const documents = [document({ id: 'd1', clientId: 'c2' }), document({ id: 'd2', clientId: 'c1' })]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository(clients),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.groups.map(g => g.client.id)).toEqual(['c1', 'c2'])
  })

  it('breaks ties in client name by client id', async () => {
    const clients = [client({ id: 'c2', name: 'Same' }), client({ id: 'c1', name: 'Same' })]
    const documents = [document({ id: 'd1', clientId: 'c2' }), document({ id: 'd2', clientId: 'c1' })]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository(clients),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.groups.map(g => g.client.id)).toEqual(['c1', 'c2'])
  })

  it('sorts documents within a group by createdAt descending', async () => {
    const documents = [
      document({ id: 'older', createdAt: '2026-08-20T10:00:00.000Z' }),
      document({ id: 'newer', createdAt: '2026-08-22T10:00:00.000Z' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.groups[0]!.documents.map(d => d.id)).toEqual(['newer', 'older'])
  })

  it('filters documents by status while keeping totals over the full dataset', async () => {
    const documents = [
      document({ id: 'd1', status: 'pending' }),
      document({ id: 'd2', status: 'failed' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ status: 'failed' })

    expect(view.filteredDocuments).toBe(1)
    expect(view.totalDocuments).toBe(2)
    expect(view.groups[0]!.documents.map(d => d.id)).toEqual(['d2'])
    expect(view.totals.failed).toBe(1)
  })

  it('hides groups that become empty after filtering', async () => {
    const clients = [client({ id: 'c1' }), client({ id: 'c2', name: 'Zeta' })]
    const documents = [
      document({ id: 'd1', clientId: 'c1', status: 'pending' }),
      document({ id: 'd2', clientId: 'c2', status: 'failed' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository(clients),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ status: 'failed' })

    expect(view.groups.map(g => g.client.id)).toEqual(['c2'])
  })

  it('filtering by "processed" also matches "approved" documents, consistent with the processedToday total', async () => {
    const documents = [
      document({ id: 'd1', status: 'processed' }),
      document({ id: 'd2', status: 'approved' }),
      document({ id: 'd3', status: 'pending' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ status: 'processed' })

    expect(view.filteredDocuments).toBe(2)
    expect(view.groups[0]!.documents.map(d => d.id).sort()).toEqual(['d1', 'd2'])
  })

  it('does not break when a document references a client that no longer exists', async () => {
    const documents = [document({ id: 'd1', clientId: 'missing-client' })]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.groups).toEqual([])
    expect(view.totalDocuments).toBe(1)
  })

  it('does not break when a client has no documents', async () => {
    const useCase = new ListInbox(
      new FakeDocumentRepository([]),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.groups).toEqual([])
  })

  it('computes unprocessed as pending + classifying + running_ocr', async () => {
    const documents = [
      document({ id: 'd1', status: 'pending' }),
      document({ id: 'd2', status: 'classifying' }),
      document({ id: 'd3', status: 'running_ocr' }),
      document({ id: 'd4', status: 'processed' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.totals.unprocessed).toBe(3)
  })

  it('computes processedToday against the injected now, in local time', async () => {
    const now = new Date('2026-08-22T23:00:00.000Z')
    const documents = [
      document({ id: 'today', status: 'processed', processedAt: '2026-08-22T10:00:00.000Z' }),
      document({ id: 'yesterday', status: 'processed', processedAt: '2026-08-21T10:00:00.000Z' })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ now })

    expect(view.totals.processedToday).toBe(1)
  })

  it('counts approved documents as processed, like the server does', async () => {
    const now = new Date('2026-08-22T23:00:00.000Z')
    const documents = [document({ id: 'd1', status: 'approved', processedAt: '2026-08-22T10:00:00.000Z' })]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ now })

    expect(view.totals.processedToday).toBe(1)
    expect(view.totals.unprocessed).toBe(0)
    expect(view.totals.failed).toBe(0)
  })

  it('computes avgProcessingMs over documents processed today', async () => {
    const now = new Date('2026-08-22T12:00:00.000Z')
    const documents = [
      document({
        id: 'd1',
        status: 'processed',
        createdAt: '2026-08-22T10:00:00.000Z',
        processedAt: '2026-08-22T10:01:00.000Z',
        sourceId: null
      }),
      document({
        id: 'd2',
        status: 'processed',
        createdAt: '2026-08-22T10:00:00.000Z',
        processedAt: '2026-08-22T10:03:00.000Z',
        sourceId: null
      })
    ]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ now })

    expect(view.totals.avgProcessingMs).toBe(120000)
  })

  it('returns avgProcessingMs = null when nothing was processed today', async () => {
    const now = new Date('2026-08-22T12:00:00.000Z')
    const documents = [document({ id: 'd1', status: 'pending' })]
    const useCase = new ListInbox(
      new FakeDocumentRepository(documents),
      new FakeClientRepository([client({})]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute({ now })

    expect(view.totals.avgProcessingMs).toBeNull()
  })

  it('resolves documentTypesById from the document type repository', async () => {
    const types = [{
      id: 't1',
      name: 'Bank statement',
      description: '',
      fields: [],
      taxYears: [],
      sampleDocumentId: null,
      extractionPrompt: '',
      extractionSchema: {},
      active: true,
      createdAt: '2026-01-01'
    }]
    const useCase = new ListInbox(
      new FakeDocumentRepository([]),
      new FakeClientRepository([]),
      new FakeDocumentTypeRepository(types)
    )

    const view = await useCase.execute()

    expect(view.documentTypesById['t1']).toEqual(types[0])
  })

  it('reports the parsable sources, so a document read by one can be named', async () => {
    // Such a document has no type by design; without this the inbox would call
    // the exogena "unclassified", which is exactly what it is not.
    const useCase = new ListInbox(
      new FakeDocumentRepository([document({ id: 'd1', clientId: 'c1', sourceId: 'exogena_report' })]),
      new FakeClientRepository([client({ id: 'c1' })]),
      new FakeDocumentTypeRepository([])
    )

    const view = await useCase.execute()

    expect(view.documentSourcesById.exogena_report).toEqual(SOURCES[0])
  })
})
