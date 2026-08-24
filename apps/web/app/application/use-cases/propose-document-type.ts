import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  DocumentTypeRepository,
  ProposeDocumentTypeInput
} from '~/application/ports/document-type-repository'

export class ProposeDocumentType {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    return this.documentTypes.propose(input)
  }
}
