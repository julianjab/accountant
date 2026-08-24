import type { DocumentTypeUpdate } from '~/domain/entities/document-type'
import type {
  CreateDocumentTypeInput,
  DocumentTypeRepository
} from '~/application/ports/document-type-repository'

export class CreateDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(input: CreateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    return this.documentTypes.create(input)
  }
}
