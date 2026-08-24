import { describe, expect, it } from 'vitest'
import type { ConceptMapping, ConceptMappingDraft } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'
import { GetConceptMapping } from '~/application/use-cases/get-concept-mapping'

const MAPPING: ConceptMapping = {
  documentTypeId: 'dt-1',
  kindId: 'exogena_dian',
  entries: [
    {
      fieldPath: 'accounts[].balance',
      conceptId: 'dian:saldo-cuentas-bancarias',
      accountPath: 'accounts[].number',
      sign: 1
    }
  ],
  reporterPath: 'bank_tax_id',
  reporterNamePath: 'bank_name',
  periodPath: 'year'
}

class FakeConceptMappingRepository implements ConceptMappingRepository {
  constructor(private readonly mapping: ConceptMapping | null) {}

  listKinds(): Promise<ReconciliationKind[]> {
    throw new Error('not implemented')
  }

  get(_kindId: string, _documentTypeId: string): Promise<ConceptMapping | null> {
    return Promise.resolve(this.mapping)
  }

  save(
    _kindId: string,
    _documentTypeId: string,
    _draft: ConceptMappingDraft
  ): Promise<ConceptMapping> {
    throw new Error('not implemented')
  }
}

describe('GetConceptMapping', () => {
  it('returns the mapping stored for the document type', async () => {
    const useCase = new GetConceptMapping(new FakeConceptMappingRepository(MAPPING))

    await expect(useCase.execute('exogena_dian', 'dt-1')).resolves.toEqual(MAPPING)
  })

  it('returns null for a document type that has not been mapped yet', async () => {
    const useCase = new GetConceptMapping(new FakeConceptMappingRepository(null))

    await expect(useCase.execute('exogena_dian', 'dt-1')).resolves.toBeNull()
  })

  it('reports a mapping the server cleared as no mapping at all', async () => {
    const cleared: ConceptMapping = {
      ...MAPPING,
      entries: [],
      reporterPath: null
    }
    const useCase = new GetConceptMapping(new FakeConceptMappingRepository(cleared))

    await expect(useCase.execute('exogena_dian', 'dt-1')).resolves.toBeNull()
  })
})
