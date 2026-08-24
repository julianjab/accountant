import type { DocumentSource } from '~/domain/entities/document-source'
import type { DocumentRepository } from '~/application/ports/document-repository'

export class ListDocumentSources {
  constructor(private readonly documents: DocumentRepository) {}

  /** The sources that could read this file, given its media type.
   *
   * Filtered rather than listed whole: offering a reviewer a source its parser
   * would refuse turns a choice into a guess, and the refusal only arrives
   * after they have made it.
   */
  async execute(mimeType?: string): Promise<DocumentSource[]> {
    const sources = await this.documents.listSources()
    if (!mimeType) {
      return sources
    }
    return sources.filter(source => source.mediaTypes.includes(mimeType))
  }
}
