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
  /** Reads the document and signs off on the result, in one call.
   *
   * A document only reaches the review screen because the pipeline could make
   * nothing of it, so this extracts first — by a dedicated parser or by OCR
   * against the configured types, whichever the file calls for — and rebuilds
   * the client's cross-check from what it read. */
  approve: (id: string, approvedBy?: string) => Promise<ClientDocument>
}
