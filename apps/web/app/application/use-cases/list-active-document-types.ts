import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

export class ListActiveDocumentTypes {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(): Promise<DocumentType[]> {
    return this.documentTypes.listActive()
  }
}
