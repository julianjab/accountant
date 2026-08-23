import type { DocumentType } from '~/domain/entities/document-type'

export interface DefineDocumentTypeInput {
  name: string
  description: string
  sampleFile: File
}

export interface DocumentTypeRepository {
  listActive: () => Promise<DocumentType[]>
  list: () => Promise<DocumentType[]>
  define: (input: DefineDocumentTypeInput) => Promise<DocumentType>
}
