import type { DocumentTypeUpdate } from '~/domain/entities/document-type'
import type {
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'

export class UpdateDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(id: string, changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    return this.documentTypes.update(id, changes)
  }
}
