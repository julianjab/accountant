import type { DocumentType, DocumentTypeUpdate } from '~/domain/entities/document-type'

export interface DefineDocumentTypeInput {
  name: string
  description: string
  sampleFile: File
}

/** Every field is optional: the configuration screen sends only what it
 * changed, so two people editing different parts of a type do not overwrite
 * each other's work. */
export interface UpdateDocumentTypeInput {
  name?: string
  description?: string
  active?: boolean
  extractionPrompt?: string
  extractionSchema?: Record<string, unknown>
}

export interface DocumentTypeRepository {
  listActive: () => Promise<DocumentType[]>
  list: () => Promise<DocumentType[]>
  define: (input: DefineDocumentTypeInput) => Promise<DocumentType>
  update: (id: string, changes: UpdateDocumentTypeInput) => Promise<DocumentTypeUpdate>
}
