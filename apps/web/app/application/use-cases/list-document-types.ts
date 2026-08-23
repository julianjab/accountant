import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

export class ListDocumentTypes {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(): Promise<DocumentType[]> {
    return this.documentTypes.list()
  }
}
