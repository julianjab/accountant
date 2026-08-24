import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class ApproveDocument {
  constructor(private readonly documents: DocumentRepository) {}

  execute(id: string, approvedBy?: string): Promise<ClientDocument> {
    return this.documents.approve(id, approvedBy)
  }
}
