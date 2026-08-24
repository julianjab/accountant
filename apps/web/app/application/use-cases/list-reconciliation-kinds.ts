import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'

export class ListReconciliationKinds {
  constructor(private readonly mappings: ConceptMappingRepository) {}

  execute(): Promise<ReconciliationKind[]> {
    return this.mappings.listKinds()
  }
}
