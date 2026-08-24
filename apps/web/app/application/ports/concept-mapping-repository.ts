import type { ConceptMapping, ConceptMappingDraft } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'

export interface ConceptMappingRepository {
  /** The reconciliation models on offer, each carrying the vocabulary its
   * document types may be mapped onto. */
  listKinds: () => Promise<ReconciliationKind[]>
  /** The mapping stored for a document type, or null when it has none yet —
   * which the configuration screen shows as "not mapped", not as a failure. */
  get: (kindId: string, documentTypeId: string) => Promise<ConceptMapping | null>
  save: (
    kindId: string,
    documentTypeId: string,
    draft: ConceptMappingDraft
  ) => Promise<ConceptMapping>
}
