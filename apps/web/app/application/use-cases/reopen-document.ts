import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class ReopenDocument {
  constructor(private readonly documents: DocumentRepository) {}

  execute(id: string): Promise<ClientDocument> {
    return this.documents.reopen(id)
  }
}
