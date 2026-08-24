import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

export class GetDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  /** Picked out of the full list because the server exposes no by-id endpoint;
   * the list includes inactive types, which an editor has to be able to open. */
  async execute(id: string): Promise<DocumentType | null> {
    const documentTypes = await this.documentTypes.list()
    return documentTypes.find(documentType => documentType.id === id) ?? null
  }
}
