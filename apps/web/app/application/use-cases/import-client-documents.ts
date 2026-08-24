import type {
  ClientDocumentsImport,
  DocumentRepository
} from '~/application/ports/document-repository'

export class ImportClientDocuments {
  constructor(private readonly documents: DocumentRepository) {}

  execute(clientId: string): Promise<ClientDocumentsImport> {
    return this.documents.importForClient(clientId)
  }
}
