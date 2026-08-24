import type { ConceptMapping, ConceptMappingDraft } from '~/domain/entities/concept-mapping'
import { UnusableConceptMappingError } from '~/domain/errors/unusable-concept-mapping-error'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'

export class SaveConceptMapping {
  constructor(private readonly mappings: ConceptMappingRepository) {}

  execute(
    kindId: string,
    documentTypeId: string,
    draft: ConceptMappingDraft
  ): Promise<ConceptMapping> {
    // Facts are attributed to the party that reported them, so without a
    // reporter path the projection discards every entry below. Refusing here
    // keeps a half-configured type from looking configured.
    if (draft.entries.length > 0 && !draft.reporterPath) {
      return Promise.reject(new UnusableConceptMappingError('missingReporterPath'))
    }
    return this.mappings.save(kindId, documentTypeId, draft)
  }
}
