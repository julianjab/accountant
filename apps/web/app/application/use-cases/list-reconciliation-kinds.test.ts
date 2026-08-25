import { describe, expect, it } from 'vitest'
import type { ConceptMapping, ConceptMappingDraft } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'
import { ListReconciliationKinds } from '~/application/use-cases/list-reconciliation-kinds'

const KIND: ReconciliationKind = {
  id: 'exogena_dian',
  label: 'Exógena DIAN',
  periodGranularity: 'year',
  answers: {},
  spineConcepts: [],
  evidenceConcepts: [
    {
      id: 'dian:saldo-cuentas-bancarias',
      label: 'Saldo de cuentas bancarias',
      role: 'evidence',
      description: ''
    }
  ]
}

class FakeConceptMappingRepository implements ConceptMappingRepository {
  listKinds(): Promise<ReconciliationKind[]> {
    return Promise.resolve([KIND])
  }

  get(_kindId: string, _documentTypeId: string): Promise<ConceptMapping | null> {
    throw new Error('not implemented')
  }

  save(
    _kindId: string,
    _documentTypeId: string,
    _draft: ConceptMappingDraft
  ): Promise<ConceptMapping> {
    throw new Error('not implemented')
  }
}

describe('ListReconciliationKinds', () => {
  it('returns each kind with the vocabulary a field can be mapped onto', async () => {
    const useCase = new ListReconciliationKinds(new FakeConceptMappingRepository())

    const kinds = await useCase.execute()

    expect(kinds).toEqual([KIND])
  })
})
