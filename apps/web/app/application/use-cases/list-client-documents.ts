import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class ListClientDocuments {
  constructor(private readonly documents: DocumentRepository) {}

  execute(clientId: string): Promise<ClientDocument[]> {
    return this.documents.listByClient(clientId)
  }
}
