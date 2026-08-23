import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class GetDocumentExtractedData {
  constructor(private readonly documents: DocumentRepository) {}

  execute(id: string): Promise<ExtractedData | null> {
    return this.documents.getExtractedData(id)
  }
}
