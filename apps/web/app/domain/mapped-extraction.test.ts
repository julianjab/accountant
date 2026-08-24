import { describe, expect, it } from 'vitest'
import type { ConceptMapping, ConceptMappingEntry } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import { childPath, conceptsByPath } from '~/domain/mapped-extraction'

function entry(overrides: Partial<ConceptMappingEntry> & { fieldPath: string }): ConceptMappingEntry {
  return {
    conceptId: 'bank:saldo',
    accountPath: null,
    sign: 1,
    spineConceptId: null,
    perAccount: false,
    ...overrides
  }
}

function mapping(entries: ConceptMappingEntry[]): ConceptMapping {
  return {
    documentTypeId: 'type-1',
    kindId: 'exogena_dian',
    entries,
    reporterPath: 'nit',
    reporterNamePath: null,
    periodPath: null,
    reporterTaxId: null,
    reporterName: null,
    period: null
  }
}

const KIND: ReconciliationKind = {
  id: 'exogena_dian',
  label: 'Exógena',
  periodGranularity: 'year',
  spineConcepts: [
    { id: 'dian:saldo-cuentas', label: 'Saldo de cuentas bancarias', role: 'spine', description: '' }
  ],
  evidenceConcepts: [
    { id: 'bank:saldo', label: 'Saldo de cuentas de ahorro', role: 'evidence', description: '' },
    { id: 'bank:gmf', label: 'GMF pagado', role: 'evidence', description: '' }
  ]
}

describe('conceptsByPath', () => {
  it('names the concept and the line of the base report it answers', () => {
    const byPath = conceptsByPath(
      mapping([
        entry({
          fieldPath: 'saldo_disponible.saldo_cuenta_ahorros',
          spineConceptId: 'dian:saldo-cuentas'
        })
      ]),
      KIND
    )

    expect(byPath.get('saldo_disponible.saldo_cuenta_ahorros')).toEqual({
      conceptLabel: 'Saldo de cuentas de ahorro',
      spineLabel: 'Saldo de cuentas bancarias',
      inverted: false
    })
  })

  it('leaves the spine label empty for a field nothing compares', () => {
    const byPath = conceptsByPath(mapping([entry({ fieldPath: 'gmf.valor', conceptId: 'bank:gmf' })]), KIND)

    expect(byPath.get('gmf.valor')?.spineLabel).toBeNull()
    expect(byPath.get('gmf.valor')?.conceptLabel).toBe('GMF pagado')
  })

  it('keeps a path inside a list in the mapping notation, so a row can find it', () => {
    const byPath = conceptsByPath(mapping([entry({ fieldPath: 'obligaciones[].capital' })]), KIND)

    expect(byPath.has('obligaciones[].capital')).toBe(true)
  })

  it('reports a field the document states with the opposite sign', () => {
    const byPath = conceptsByPath(mapping([entry({ fieldPath: 'retencion', sign: -1 })]), KIND)

    expect(byPath.get('retencion')?.inverted).toBe(true)
  })

  it('names a concept by its id when the kind no longer publishes it', () => {
    const byPath = conceptsByPath(mapping([entry({ fieldPath: 'gmf.valor', conceptId: 'bank:retirado' })]), KIND)

    expect(byPath.get('gmf.valor')?.conceptLabel).toBe('bank:retirado')
  })

  it('has nothing to say for a type that was never mapped', () => {
    expect(conceptsByPath(null, KIND).size).toBe(0)
  })
})

describe('childPath', () => {
  it('builds the path the mapping uses as the value tree is walked', () => {
    expect(childPath('', 'saldo_disponible', false)).toBe('saldo_disponible')
    expect(childPath('saldo_disponible', 'saldo_cuenta_ahorros', false)).toBe('saldo_disponible.saldo_cuenta_ahorros')
    expect(childPath('obligaciones', 'capital', true)).toBe('obligaciones[].capital')
  })
})
