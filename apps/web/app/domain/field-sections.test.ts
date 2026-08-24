import { describe, expect, it } from 'vitest'
import type { DocumentTypeField } from '~/domain/entities/document-type'
import {
  descriptionsForKnownPaths,
  mergeDescriptions,
  groupBySection,
  hasUsefulSections,
  isUnderdescribed,
  labelFor,
  orderedSectionNames,
  rootKey,
  sectionFor
} from '~/domain/field-sections'

function field(path: string, section: string, label = path): DocumentTypeField {
  return { path, label, role: 'context', section, sampleValue: '' }
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

describe('mergeDescriptions', () => {
  it('adds a recovered description for a field that had none', () => {
    const merged = mergeDescriptions([field('nit', 'Emisor')], [field('gmf', 'GMF')])

    expect(merged.map(f => f.path)).toEqual(['nit', 'gmf'])
  })

  it('keeps the stored description when both describe the same field', () => {
    // The stored one was curated; the recovered one is today's guess.
    const merged = mergeDescriptions(
      [field('nit', 'Emisor', 'NIT corregido a mano')],
      [field('nit', 'Otro bloque', 'NIT')]
    )

    expect(merged).toEqual([field('nit', 'Emisor', 'NIT corregido a mano')])
  })

  it('never drops a stored description the recovery did not match', () => {
    // The server replaces descriptions wholesale, so anything missing here is
    // deleted — an action offering to add labels would be destroying them.
    const merged = mergeDescriptions(FIELDS, [])

    expect(merged).toEqual([...FIELDS])
  })

  it('fills in the sample value of a field that was named but never valued', () => {
    // Every type saved before values were carried. Merging whole fields left
    // these unfixable: the path was there, so the reading that had just found
    // the value on the paper was thrown away.
    const stored = { ...field('nit', 'Emisor', 'NIT'), sampleValue: '' }
    const fresh = { ...field('nit', 'Emisor', 'NIT'), sampleValue: '890.903.938' }

    expect(mergeDescriptions([stored], [fresh])[0]!.sampleValue).toBe('890.903.938')
  })

  it('replaces a label that only repeats the field name', () => {
    // What the schema fallback produces when a proposal describes nothing: a
    // label in the data and no label on screen.
    const stored = field('agente_retenedor.nit', '', 'nit')
    const fresh = field('agente_retenedor.nit', 'Agente retenedor', 'NIT del agente')

    expect(mergeDescriptions([stored], [fresh])[0]).toEqual({
      ...fresh,
      role: stored.role
    })
  })

  it('still refuses to overwrite a label someone wrote', () => {
    const merged = mergeDescriptions(
      [{ ...field('nit', 'Emisor', 'NIT corregido a mano'), sampleValue: '1' }],
      [{ ...field('nit', 'Otro bloque', 'NIT'), sampleValue: '2' }]
    )

    expect(merged[0]!.label).toBe('NIT corregido a mano')
    expect(merged[0]!.section).toBe('Emisor')
    expect(merged[0]!.sampleValue).toBe('1')
  })
})

describe('isUnderdescribed', () => {
  it('is true for a field whose label only repeats its own name', () => {
    expect(isUnderdescribed(field('agente_retenedor.nit', 'Emisor', 'nit'))).toBe(true)
  })

  it('is true for a field with no sample value, however well named', () => {
    expect(isUnderdescribed(field('nit', 'Emisor', 'NIT'))).toBe(true)
  })

  it('is false once the paper has told us everything about it', () => {
    expect(
      isUnderdescribed({ ...field('nit', 'Emisor', 'NIT'), sampleValue: '890.903.938' })
    ).toBe(false)
  })
})
