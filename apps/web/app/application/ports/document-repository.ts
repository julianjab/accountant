import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'

export interface DocumentRepository {
  getById: (id: string) => Promise<ClientDocument>
  getExtractedData: (id: string) => Promise<ExtractedData | null>
  listByClient: (clientId: string) => Promise<ClientDocument[]>
}
