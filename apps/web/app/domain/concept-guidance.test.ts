import { describe, expect, it } from 'vitest'
import type { ReconciliationKind } from './entities/reconciliation-kind'
import {
  conceptNamespace,
  derivedSpineFor,
  isPairDeclared,
  namespacesInUse,
  rankConcepts,
  rankSpineConcepts,
  spineAnsweredBy
} from './concept-guidance'

function concept(id: string) {
  return { id, label: id, role: 'evidence', description: '' }
}

const KIND: ReconciliationKind = {
  id: 'exogena_dian',
  label: 'Exógena',
  periodGranularity: 'year',
  spineConcepts: [
    concept('dian:pagos-salarios'),
    concept('dian:cesantias-abonadas'),
    concept('dian:cesantias-consignadas'),
    concept('dian:saldo-cuentas-bancarias')
  ],
  evidenceConcepts: [
    concept('payroll:cert_pagos_salarios'),
    concept('payroll:cert_cesantias_consignadas'),
    concept('payroll:cert_otros_pagos'),
    concept('bank:cert_saldo_cuentas_ahorro')
  ],
  answers: {
    'payroll:cert_pagos_salarios': ['dian:pagos-salarios'],
    'payroll:cert_cesantias_consignadas': ['dian:cesantias-abonadas', 'dian:cesantias-consignadas'],
    'bank:cert_saldo_cuentas_ahorro': ['dian:saldo-cuentas-bancarias']
  }
}

describe('derivedSpineFor', () => {
  it('answers the line itself when the rules leave exactly one', () => {
    // The question the screen used to ask thirty-two times on one certificate,
    // with one legal answer each time.
    expect(derivedSpineFor(KIND, 'payroll:cert_pagos_salarios')).toBe('dian:pagos-salarios')
  })

  it('leaves the choice open when the rules declare more than one', () => {
    // Whether severance was credited or paid into the fund is a real question
    // about the paper, and the model cannot answer it.
    expect(derivedSpineFor(KIND, 'payroll:cert_cesantias_consignadas')).toBeNull()
  })

  it('leaves it open for a concept no rule covers', () => {
    expect(derivedSpineFor(KIND, 'payroll:cert_otros_pagos')).toBeNull()
  })

  it('answers nothing before a concept has been chosen', () => {
    expect(derivedSpineFor(KIND, null)).toBeNull()
    expect(derivedSpineFor(null, 'payroll:cert_pagos_salarios')).toBeNull()
  })
})

describe('isPairDeclared', () => {
  it('accepts the pair the rules compare', () => {
    expect(isPairDeclared(KIND, 'payroll:cert_pagos_salarios', 'dian:pagos-salarios')).toBe(true)
  })

  it('flags a pair no rule compares, which stores fine and reconciles nothing', () => {
    expect(
      isPairDeclared(KIND, 'payroll:cert_pagos_salarios', 'dian:saldo-cuentas-bancarias')
    ).toBe(false)
  })

  it('does not call a concept with no declared answer a mismatch', () => {
    // It is a gap in the rule pack, said in its own words, not a wrong choice.
    expect(isPairDeclared(KIND, 'payroll:cert_otros_pagos', 'dian:pagos-salarios')).toBe(true)
  })

  it('says nothing about a half-answered row', () => {
    expect(isPairDeclared(KIND, 'payroll:cert_pagos_salarios', null)).toBe(true)
  })
})

describe('spineAnsweredBy', () => {
  it('lists both claims a concept may back', () => {
    expect(spineAnsweredBy(KIND, 'payroll:cert_cesantias_consignadas')).toEqual([
      'dian:cesantias-abonadas',
      'dian:cesantias-consignadas'
    ])
  })

  it('reads a server that never sent the guidance as no guidance', () => {
    expect(spineAnsweredBy({ ...KIND, answers: {} }, 'payroll:cert_pagos_salarios')).toEqual([])
  })
})

describe('narrowing the catalogue to the document', () => {
  it('reads what kind of paper this is off the answers already given', () => {
    expect([...namespacesInUse(['payroll:cert_pagos_salarios', null, 'payroll:cert_otros_pagos'])])
      .toEqual(['payroll'])
  })

  it('offers everything while nothing has been named yet', () => {
    const split = rankConcepts(KIND.evidenceConcepts, new Set())

    expect(split.likely).toEqual([])
    expect(split.rest).toHaveLength(4)
  })

  it('floats this document\'s concepts up without hiding the rest', () => {
    // A certificate that turns out to certify two things must not have the
    // second hidden from it because of what the first row said.
    const split = rankConcepts(KIND.evidenceConcepts, new Set(['payroll']))

    expect(split.likely.map(c => c.id)).toEqual([
      'payroll:cert_pagos_salarios',
      'payroll:cert_cesantias_consignadas',
      'payroll:cert_otros_pagos'
    ])
    expect(split.rest.map(c => c.id)).toEqual(['bank:cert_saldo_cuentas_ahorro'])
  })

  it('floats the lines this figure backs up, and keeps the others reachable', () => {
    // Reachable is the point: a correspondence wired wrong has to be fixable
    // from this screen rather than needing a code change.
    const split = rankSpineConcepts(KIND.spineConcepts, ['dian:cesantias-abonadas'])

    expect(split.likely.map(c => c.id)).toEqual(['dian:cesantias-abonadas'])
    expect(split.rest).toHaveLength(3)
  })

  it('reads an id with no namespace as belonging to none', () => {
    expect(conceptNamespace('suelto')).toBe('')
  })
})
