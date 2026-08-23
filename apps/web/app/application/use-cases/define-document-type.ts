import type { DocumentType } from '~/domain/entities/document-type'
import type { DefineDocumentTypeInput, DocumentTypeRepository } from '~/application/ports/document-type-repository'

export class DefineDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(input: DefineDocumentTypeInput): Promise<DocumentType> {
    return this.documentTypes.define(input)
  }
}
