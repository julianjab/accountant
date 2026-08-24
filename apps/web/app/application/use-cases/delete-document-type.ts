import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

export class DeleteDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(id: string): Promise<void> {
    return this.documentTypes.remove(id)
  }
}
