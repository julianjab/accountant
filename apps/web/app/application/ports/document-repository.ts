import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'

export interface DocumentListFilter {
  status?: DocumentStatus
}

export interface ClientDocumentsImport {
  imported: ClientDocument[]
  failed: ClientDocument[]
  /** Files with no readable bytes, so no document exists for them at all. */
  unreadable: string[]
  skipped: number
}

export interface DocumentRepository {
  getById: (id: string) => Promise<ClientDocument>
  getExtractedData: (id: string) => Promise<ExtractedData | null>
  listByClient: (clientId: string) => Promise<ClientDocument[]>
  list: (filter?: DocumentListFilter) => Promise<ClientDocument[]>
  /** Processes whatever is already in the client's storage folder.
   *
   * Drive only notifies about changes made after a subscription starts, so
   * anything already in the folder — or anything that arrived while no watch
   * was active — can enter no other way. */
  importForClient: (clientId: string) => Promise<ClientDocumentsImport>
}
