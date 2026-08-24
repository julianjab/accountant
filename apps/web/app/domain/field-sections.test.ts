import { describe, expect, it } from 'vitest'
import type { DocumentTypeField } from '~/domain/entities/document-type'
import {
  descriptionsForKnownPaths,
  groupBySection,
  hasUsefulSections,
  labelFor,
  orderedSectionNames,
  rootKey,
  sectionFor
} from '~/domain/field-sections'

function field(path: string, section: string, label = path): DocumentTypeField {
  return { path, label, role: 'context', section }
}

const FIELDS: DocumentTypeField[] = [
  field('nit', 'Datos del emisor', 'NIT'),
  field('razon_social', 'Datos del emisor', 'Razón social'),
  field('cuentas[].numero', 'Cuentas de ahorro', 'Número de cuenta'),
  field('cuentas[].saldo', 'Cuentas de ahorro', 'Saldo a 31 de diciembre'),
  field('gmf', 'Gravamen a los movimientos financieros', 'GMF')
]

describe('rootKey', () => {
  it('reduces a nested path to the top-level key extracted data is keyed by', () => {
    expect(rootKey('cuentas[].saldo')).toBe('cuentas')
    expect(rootKey('gmf')).toBe('gmf')
  })
})

describe('labelFor', () => {
  it('gives the name the document uses', () => {
    expect(labelFor('cuentas[].saldo', FIELDS)).toBe('Saldo a 31 de diciembre')
  })

  it('falls back to the path, because a row with no name at all is unreadable', () => {
    expect(labelFor('retencion', FIELDS)).toBe('retencion')
  })

  it('falls back when a stored label is blank rather than showing an empty row', () => {
    expect(labelFor('x', [field('x', 'S', '')])).toBe('x')
  })
})

describe('sectionFor', () => {
  it('matches the described field exactly', () => {
    expect(sectionFor('gmf', FIELDS)).toBe('Gravamen a los movimientos financieros')
  })

  it('places a whole extracted array under the heading its own columns carry', () => {
    // Extracted data is keyed by `cuentas`; only `cuentas[].saldo` is described.
    expect(sectionFor('cuentas', FIELDS)).toBe('Cuentas de ahorro')
  })

  it('is empty for a path the type says nothing about', () => {
    expect(sectionFor('sorpresa', FIELDS)).toBe('')
  })
})

describe('groupBySection', () => {
  const keys = ['gmf', 'cuentas', 'razon_social', 'nit']

  it('returns sections in the order the document declares them, not alphabetically', () => {
    const sections = groupBySection(keys, key => key, FIELDS)

    expect(sections.map(s => s.name)).toEqual([
      'Datos del emisor',
      'Cuentas de ahorro',
      'Gravamen a los movimientos financieros'
    ])
  })

  it('keeps every item, so nothing extracted vanishes from the screen', () => {
    const sections = groupBySection(keys, key => key, FIELDS)

    expect(sections.flatMap(s => s.items).sort()).toEqual([...keys].sort())
  })

  it('gathers undescribed fields into one trailing unnamed group', () => {
    const sections = groupBySection(['nit', 'sorpresa'], key => key, FIELDS)

    expect(sections.at(-1)).toEqual({ name: '', items: ['sorpresa'] })
  })

  it('drops sections no extracted field landed in', () => {
    const sections = groupBySection(['nit'], key => key, FIELDS)

    expect(sections).toEqual([{ name: 'Datos del emisor', items: ['nit'] }])
  })

  it('puts everything in the unnamed group when the type has no descriptions', () => {
    const sections = groupBySection(keys, key => key, [])

    expect(sections).toEqual([{ name: '', items: keys }])
  })
})

describe('hasUsefulSections', () => {
  it('is false with no descriptions, which is every type created before them', () => {
    expect(hasUsefulSections([])).toBe(false)
  })

  it('is false for a single section, a heading that separates nothing', () => {
    expect(hasUsefulSections([field('a', 'Todo'), field('b', 'Todo')])).toBe(false)
  })

  it('is true once the document is actually divided', () => {
    expect(hasUsefulSections(FIELDS)).toBe(true)
  })
})

describe('orderedSectionNames', () => {
  it('lists each section once, first appearance first', () => {
    expect(orderedSectionNames(FIELDS)).toEqual([
      'Datos del emisor',
      'Cuentas de ahorro',
      'Gravamen a los movimientos financieros'
    ])
  })
})

describe('descriptionsForKnownPaths', () => {
  it('keeps the descriptions the stored schema can use', () => {
    const kept = descriptionsForKnownPaths(FIELDS, ['nit', 'gmf'])

    expect(kept.map(f => f.path)).toEqual(['nit', 'gmf'])
  })

  it('drops a description for a path the schema never declared', () => {
    // A fresh run of the model invents its own field names and need not agree
    // with the run that produced the stored schema. Kept, the label would name
    // a field that is never extracted and read on screen as one that exists.
    const kept = descriptionsForKnownPaths([field('saldo_final', 'Saldos')], ['saldo'])

    expect(kept).toEqual([])
  })

  it('can legitimately recover nothing, which the caller has to be able to see', () => {
    expect(descriptionsForKnownPaths(FIELDS, [])).toEqual([])
  })
})
