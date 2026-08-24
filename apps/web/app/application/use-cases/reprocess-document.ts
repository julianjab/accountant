import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class ReprocessDocument {
  constructor(private readonly documents: DocumentRepository) {}

  execute(id: string): Promise<ClientDocument> {
    return this.documents.reprocess(id)
  }
}
