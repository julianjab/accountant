import type { DocumentTypeCreation } from '~/domain/entities/document-type'
import type {
  CreateDocumentTypeInput,
  DocumentTypeRepository
} from '~/application/ports/document-type-repository'

export class CreateDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    return this.documentTypes.create(input)
  }
}
