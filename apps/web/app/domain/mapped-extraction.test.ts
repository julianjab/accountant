import { describe, expect, it } from 'vitest'
import type { ConceptMapping, ConceptMappingEntry } from '~/domain/entities/concept-mapping'
import type { DocumentTypeField } from '~/domain/entities/document-type'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import { mappedFieldGroups, resolvePath } from '~/domain/mapped-extraction'

function field(path: string, label: string, section = 'Bloque'): DocumentTypeField {
  return { path, label, role: 'amount', section, sampleValue: '' }
}

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

const FIELDS: DocumentTypeField[] = [
  field('saldo_disponible.saldo_cuenta_ahorros', 'Saldo Cuenta Ahorros'),
  field('cuentas[].saldo', 'Saldo'),
  field('cuentas[].numero', 'Número de cuenta'),
  field('gmf.valor', 'Valor GMF')
]

describe('resolvePath', () => {
  it('reads a nested value', () => {
    expect(resolvePath({ saldo_disponible: { saldo_cuenta_ahorros: '2.241.275,17' } }, 'saldo_disponible.saldo_cuenta_ahorros'))
      .toEqual([{ value: '2.241.275,17', indices: [] }])
  })

  it('walks every element of a list, the way the projection does', () => {
    expect(resolvePath({ cuentas: [{ saldo: 10 }, { saldo: 20 }] }, 'cuentas[].saldo')).toEqual([
      { value: 10, indices: [0] },
      { value: 20, indices: [1] }
    ])
  })

  it('yields nothing for a path the document never filled in', () => {
    expect(resolvePath({ gmf: {} }, 'gmf.valor')).toEqual([])
    expect(resolvePath({}, 'cuentas[].saldo')).toEqual([])
  })
})

describe('mappedFieldGroups', () => {
  it('puts what the base report compares ahead of what it does not', () => {
    const groups = mappedFieldGroups(
      mapping([
        entry({ fieldPath: 'gmf.valor', conceptId: 'bank:gmf' }),
        entry({
          fieldPath: 'saldo_disponible.saldo_cuenta_ahorros',
          spineConceptId: 'dian:saldo-cuentas'
        })
      ]),
      { gmf: { valor: '9.946' }, saldo_disponible: { saldo_cuenta_ahorros: '2.241.275,17' } },
      FIELDS,
      KIND
    )

    expect(groups.crossed.map(f => f.fieldPath)).toEqual(['saldo_disponible.saldo_cuenta_ahorros'])
    expect(groups.crossed[0]!.label).toBe('Saldo Cuenta Ahorros')
    expect(groups.crossed[0]!.conceptLabel).toBe('Saldo de cuentas de ahorro')
    expect(groups.crossed[0]!.spineLabel).toBe('Saldo de cuentas bancarias')
    expect(groups.crossed[0]!.values).toEqual([{ value: '2.241.275,17', account: null }])
    expect(groups.uncrossed.map(f => f.conceptLabel)).toEqual(['GMF pagado'])
  })

  it('pairs each amount with the account stated on its own row', () => {
    const groups = mappedFieldGroups(
      mapping([
        entry({
          fieldPath: 'cuentas[].saldo',
          accountPath: 'cuentas[].numero',
          perAccount: true,
          spineConceptId: 'dian:saldo-cuentas'
        })
      ]),
      { cuentas: [{ saldo: 10, numero: '123' }, { saldo: 20, numero: '456' }] },
      FIELDS,
      KIND
    )

    expect(groups.crossed[0]!.values).toEqual([
      { value: 10, account: '123' },
      { value: 20, account: '456' }
    ])
  })

  it('keeps a mapped field the document never stated, because its absence is the finding', () => {
    const groups = mappedFieldGroups(
      mapping([entry({ fieldPath: 'gmf.valor', spineConceptId: 'dian:saldo-cuentas' })]),
      { gmf: {} },
      FIELDS,
      KIND
    )

    expect(groups.crossed).toHaveLength(1)
    expect(groups.crossed[0]!.values).toEqual([])
  })

  it('names a concept by its id when the kind no longer publishes it', () => {
    const groups = mappedFieldGroups(
      mapping([entry({ fieldPath: 'gmf.valor', conceptId: 'bank:retirado' })]),
      { gmf: { valor: 1 } },
      FIELDS,
      KIND
    )

    expect(groups.uncrossed[0]!.conceptLabel).toBe('bank:retirado')
  })

  it('has nothing to show for a type that was never mapped', () => {
    expect(mappedFieldGroups(null, { gmf: { valor: 1 } }, FIELDS, KIND)).toEqual({
      crossed: [],
      uncrossed: []
    })
  })
})
