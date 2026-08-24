import type { DocumentTypeField } from '~/domain/entities/document-type'
import type {
  DescribeDocumentTypeFieldsInput,
  DocumentTypeRepository
} from '~/application/ports/document-type-repository'

/**
 * Reads a sample again to recover what the document calls a type's fields.
 *
 * Deliberately not "propose the type again and keep what matches": the model
 * names its fields afresh on every proposal, so that recovered only the paths
 * two independent runs happened to agree on — on a long certificate, none.
 * This asks about the paths the type already has, so an answer is always
 * about a field that exists.
 */
export class DescribeDocumentTypeFields {
  constructor(private readonly documentTypes: DocumentTypeRepository) {}

  execute(id: string, input: DescribeDocumentTypeFieldsInput): Promise<DocumentTypeField[]> {
    return this.documentTypes.describeFields(id, input)
  }
}
