import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class RecognizeDocumentSource {
  constructor(private readonly documents: DocumentRepository) {}

  execute(id: string, sourceId: string): Promise<ClientDocument> {
    return this.documents.recognizeSource(id, sourceId)
  }
}
