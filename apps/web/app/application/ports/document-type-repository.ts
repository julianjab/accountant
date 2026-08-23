import type { DocumentType } from '~/domain/entities/document-type'

export interface DocumentTypeRepository {
  listActive: () => Promise<DocumentType[]>
}
