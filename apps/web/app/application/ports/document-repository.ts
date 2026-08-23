import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'

export interface DocumentListFilter {
  status?: DocumentStatus
}

export interface DocumentRepository {
  getById: (id: string) => Promise<ClientDocument>
  getExtractedData: (id: string) => Promise<ExtractedData | null>
  listByClient: (clientId: string) => Promise<ClientDocument[]>
  list: (filter?: DocumentListFilter) => Promise<ClientDocument[]>
}
