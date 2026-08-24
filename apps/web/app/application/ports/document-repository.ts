import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentSource } from '~/domain/entities/document-source'
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
  /** The formats a reviewer can declare a document to be.
   *
   * Needed because the classifier can never propose these: they are read by a
   * parser instead of being configured as document types, so such a file always
   * fails classification and only a person can name it. */
  listSources: () => Promise<DocumentSource[]>
  /** Reads the document with the named source's parser.
   *
   * Rejects when the file turns out not to be that source, leaving the document
   * exactly as it was — so picking the wrong one costs nothing. */
  recognizeSource: (id: string, sourceId: string) => Promise<ClientDocument>
  approve: (id: string, approvedBy?: string) => Promise<ClientDocument>
}
