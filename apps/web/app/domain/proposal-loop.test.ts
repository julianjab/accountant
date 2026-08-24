import { describe, expect, it } from 'vitest'
import type { ProposalFieldRow } from '~/domain/document-type-configuration'
import {
  carryChoices,
  isEmptySelection,
  rowsForRemovedPaths,
  toFieldSelection
} from '~/domain/proposal-loop'

function row(overrides: Partial<ProposalFieldRow> & { path: string }): ProposalFieldRow {
  return {
    label: 'Un campo',
    sampleValue: '',
    section: null,
    role: 'context',
    kept: true,
    conceptId: null,
    spineConceptId: null,
    perAccount: false,
    accountPath: null,
    ...overrides
  }
}

describe('toFieldSelection', () => {
  it('states every unticked field as a refusal, not as an absence', () => {
    // A field the model merely does not see mentioned is one it offers again
    // next round as a helpful addition — which is how a loop fails to settle.
    const selection = toFieldSelection([
      row({ path: 'saldo', kept: true }),
      row({ path: 'agente.direccion', kept: false })
    ])

    expect(selection.dropped).toEqual(['agente.direccion'])
    expect(selection.kept.map(field => field.path)).toEqual(['saldo'])
  })

  it('sends the name the person gave a field, not the one the document prints', () => {
    const selection = toFieldSelection([
      row({ path: 'gmf.valor', label: 'Valor GMF', renamedLabel: 'GMF retenido' })
    ])

    expect(selection.kept[0]!.label).toBe('GMF retenido')
  })

  it('falls back to the document’s own wording when nothing was renamed', () => {
    const selection = toFieldSelection([row({ path: 'gmf.valor', label: 'Valor GMF' })])

    expect(selection.kept[0]!.label).toBe('Valor GMF')
  })

  it('carries a per-field note trimmed, since it reaches the model as prose', () => {
    const selection = toFieldSelection([
      row({ path: 'obligaciones[].concepto', note: '  es una fila, no el total  ' })
    ])

    expect(selection.kept[0]!.note).toBe('es una fila, no el total')
  })
})

describe('isEmptySelection', () => {
  it('is empty only when nothing was kept and nothing refused', () => {
    expect(isEmptySelection({ kept: [], dropped: [], sections: [] })).toBe(true)
    expect(isEmptySelection({ kept: [], dropped: ['a'], sections: [] })).toBe(false)
    // A block instruction alone is worth sending: the reader may say what a
    // table is before they have chosen a single field out of it.
    expect(
      isEmptySelection({ kept: [], dropped: [], sections: [{ section: 'GMF', note: 'mensual' }] })
    ).toBe(false)
  })
})

describe('carryChoices', () => {
  it('keeps the tick, the name and the note the person authored', () => {
    const previous = [
      row({ path: 'saldo', kept: false, renamedLabel: 'Saldo final', note: 'el de diciembre' })
    ]

    const [carried] = carryChoices([row({ path: 'saldo', label: 'Saldo' })], previous)

    expect(carried!.kept).toBe(false)
    expect(carried!.renamedLabel).toBe('Saldo final')
    expect(carried!.note).toBe('el de diciembre')
  })

  it('lets the new reading refresh what it read, not what the person decided', () => {
    // Losing a better sample value or a corrected section on every round would
    // make the loop worse than a single shot.
    const previous = [row({ path: 'saldo', sampleValue: '', section: null })]

    const [carried] = carryChoices(
      [row({ path: 'saldo', sampleValue: '150464.81', section: 'Saldos' })],
      previous
    )

    expect(carried!.sampleValue).toBe('150464.81')
    expect(carried!.section).toBe('Saldos')
  })

  it('leaves a field the last round never had exactly as it was proposed', () => {
    const [carried] = carryChoices([row({ path: 'nuevo', kept: true })], [])

    expect(carried!.kept).toBe(true)
  })
})

describe('rowsForRemovedPaths', () => {
  it('offers a dropped field back unticked, named the way the type named it', () => {
    // Unticked because no schema declares it any more: reporting it as kept
    // would claim the type still extracts something it does not.
    const [removed] = rowsForRemovedPaths(['gmf.base_gravable'], () => 'Base gravable')

    expect(removed!.kept).toBe(false)
    expect(removed!.label).toBe('Base gravable')
  })

  it('travels in the next round’s kept list once ticked, which is what recovers it', () => {
    const rows = rowsForRemovedPaths(['gmf.base_gravable'], path => path)
    rows[0]!.kept = true

    expect(toFieldSelection(rows).kept.map(field => field.path)).toEqual(['gmf.base_gravable'])
  })
})

describe('block instructions', () => {
  it('sends what was written about a block this reading actually has', () => {
    const selection = toFieldSelection(
      [row({ path: 'gmf.valor', section: 'Gravamen a los movimientos financieros' })],
      { 'Gravamen a los movimientos financieros': '  son mensuales, no acumulados  ' }
    )

    expect(selection.sections).toEqual([
      { section: 'Gravamen a los movimientos financieros', note: 'son mensuales, no acumulados' }
    ])
  })

  it('drops a note about a block this reading no longer produces', () => {
    // It would ask the model to watch a part of the page it no longer believes
    // is there, which is worse than saying nothing.
    const selection = toFieldSelection([row({ path: 'saldo', section: 'Cuentas' })], {
      'Obligaciones a cargo': 'una fila por obligación'
    })

    expect(selection.sections).toEqual([])
  })

  it('drops a box that was opened and left alone', () => {
    const selection = toFieldSelection([row({ path: 'saldo', section: 'Cuentas' })], {
      Cuentas: '   '
    })

    expect(selection.sections).toEqual([])
  })

  it('carries a note about the fields no heading was given, like any other block', () => {
    // The leftovers are exactly where a reader is most likely to have
    // something to say, and they are keyed by the empty string.
    const selection = toFieldSelection([row({ path: 'notas', section: null })], {
      '': 'esto es el pie de página'
    })

    expect(selection.sections).toEqual([{ section: '', note: 'esto es el pie de página' }])
  })
})
