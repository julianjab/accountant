import { describe, expect, it } from 'vitest'
import type { ConceptMapping, ConceptMappingDraft } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import { UnusableConceptMappingError } from '~/domain/errors/unusable-concept-mapping-error'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'
import { SaveConceptMapping } from '~/application/use-cases/save-concept-mapping'

const DRAFT: ConceptMappingDraft = {
  entries: [
    {
      fieldPath: 'accounts[].balance',
      conceptId: 'dian:saldo-cuentas-bancarias',
      accountPath: 'accounts[].number',
      sign: 1,
      spineConceptId: 'dian:saldo-cuentas-bancarias',
      perAccount: true,
      rowLabelPath: null,
      rowLabel: null
    }
  ],
  reporterPath: 'bank_tax_id',
  reporterNamePath: 'bank_name',
  periodPath: 'year',
  reporterTaxId: null,
  reporterName: null,
  period: null
}

class FakeConceptMappingRepository implements ConceptMappingRepository {
  savedDraft: ConceptMappingDraft | null = null

  listKinds(): Promise<ReconciliationKind[]> {
    throw new Error('not implemented')
  }

  get(_kindId: string, _documentTypeId: string): Promise<ConceptMapping | null> {
    throw new Error('not implemented')
  }

  save(
    kindId: string,
    documentTypeId: string,
    draft: ConceptMappingDraft
  ): Promise<ConceptMapping> {
    this.savedDraft = draft
    return Promise.resolve({ ...draft, documentTypeId, kindId })
  }
}

describe('SaveConceptMapping', () => {
  it('saves the mapping and returns it bound to its kind and document type', async () => {
    const repository = new FakeConceptMappingRepository()
    const useCase = new SaveConceptMapping(repository)

    const saved = await useCase.execute('exogena_dian', 'dt-1', DRAFT)

    expect(repository.savedDraft).toEqual(DRAFT)
    expect(saved.documentTypeId).toBe('dt-1')
    expect(saved.kindId).toBe('exogena_dian')
  })

  it('refuses a mapping with entries but no reporting party, which could never produce a fact', async () => {
    const repository = new FakeConceptMappingRepository()
    const useCase = new SaveConceptMapping(repository)

    await expect(
      useCase.execute('exogena_dian', 'dt-1', { ...DRAFT, reporterPath: null })
    ).rejects.toBeInstanceOf(UnusableConceptMappingError)
    expect(repository.savedDraft).toBeNull()
  })

  it('saves an empty mapping without a reporting party, which is how a type is unmapped', async () => {
    const repository = new FakeConceptMappingRepository()
    const useCase = new SaveConceptMapping(repository)

    await useCase.execute('exogena_dian', 'dt-1', {
      entries: [],
      reporterPath: null,
      reporterNamePath: null,
      periodPath: null,
      reporterTaxId: null,
      reporterName: null,
      period: null
    })

    expect(repository.savedDraft?.entries).toEqual([])
  })
})
