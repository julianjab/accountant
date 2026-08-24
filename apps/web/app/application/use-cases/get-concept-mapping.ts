import type { ConceptMapping } from '~/domain/entities/concept-mapping'
import { isConceptMappingCleared } from '~/domain/entities/concept-mapping'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'

export class GetConceptMapping {
  constructor(private readonly mappings: ConceptMappingRepository) {}

  /** A cleared mapping is reported as none at all: the caller has to see "this
   * type is not mapped", not an empty mapping that looks configured. */
  async execute(kindId: string, documentTypeId: string): Promise<ConceptMapping | null> {
    const mapping = await this.mappings.get(kindId, documentTypeId)
    if (mapping === null || isConceptMappingCleared(mapping)) return null
    return mapping
  }
}
