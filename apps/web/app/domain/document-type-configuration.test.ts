import { describe, expect, it } from 'vitest'
import type { ConceptMapping, MappingChange } from '~/domain/entities/concept-mapping'
import type { SchemaField } from '~/domain/extraction-schema'
import {
  buildFieldSelections,
  configurationStatus,
  isDraftSavable,
  keptPaths,
  mappingChangeSeverity,
  shouldSaveDraft,
  toMappingDraft
} from '~/domain/document-type-configuration'

function field(path: string): SchemaField {
  return { path, name: path, type: 'string', description: '', required: false }
}

const FIELDS: SchemaField[] = [field('nit'), field('razon_social'), field('anio'), field('gmf')]

const MAPPING: ConceptMapping = {
  documentTypeId: 'dt-1',
  kindId: 'exogena_dian',
  entries: [{ fieldPath: 'gmf', conceptId: 'bank:cert_gmf_valor', accountPath: 'nit', sign: -1 }],
  reporterPath: 'nit',
  reporterNamePath: 'razon_social',
  periodPath: 'anio'
}

const NO_ROLES = { reporterPath: null, reporterNamePath: null, periodPath: null }

describe('buildFieldSelections', () => {
  it('keeps every field the schema already declares', () => {
    const selections = buildFieldSelections(FIELDS, null)

    expect(selections.every(selection => selection.kept)).toBe(true)
  })

  it('shows the concept the stored mapping assigned to each field', () => {
    const selections = buildFieldSelections(FIELDS, MAPPING)

    expect(selections.map(selection => selection.conceptId)).toEqual([
      null,
      null,
      null,
      'bank:cert_gmf_valor'
    ])
  })
})

describe('toMappingDraft', () => {
  it('maps a kept field onto the concept the user chose', () => {
    const selections = [{ path: 'gmf', kept: true, conceptId: 'bank:cert_gmf_valor' }]

    const draft = toMappingDraft(selections, { ...NO_ROLES, reporterPath: 'nit' }, null)

    expect(draft.entries).toEqual([
      { fieldPath: 'gmf', conceptId: 'bank:cert_gmf_valor', accountPath: null, sign: 1 }
    ])
  })

  it('leaves a kept field with no concept out of the mapping', () => {
    const selections = [{ path: 'gmf', kept: true, conceptId: null }]

    expect(toMappingDraft(selections, NO_ROLES, null).entries).toEqual([])
  })

  it('drops the entry of a field the user removed from the schema', () => {
    const selections = [{ path: 'gmf', kept: false, conceptId: 'bank:cert_gmf_valor' }]

    expect(toMappingDraft(selections, NO_ROLES, MAPPING).entries).toEqual([])
  })

  it('preserves the sign an existing entry was curated with', () => {
    const selections = buildFieldSelections(FIELDS, MAPPING)

    const draft = toMappingDraft(selections, MAPPING, MAPPING)

    expect(draft.entries[0]).toMatchObject({ sign: -1, accountPath: 'nit' })
  })

  it('clears an account path whose field is no longer extracted', () => {
    const selections = buildFieldSelections(FIELDS, MAPPING).map(selection =>
      selection.path === 'nit' ? { ...selection, kept: false } : selection
    )

    const draft = toMappingDraft(selections, MAPPING, MAPPING)

    expect(draft.entries[0]?.accountPath).toBeNull()
  })

  it('clears the reporting-party path when its field is removed', () => {
    const selections = buildFieldSelections(FIELDS, MAPPING).map(selection =>
      selection.path === 'nit' ? { ...selection, kept: false } : selection
    )

    expect(toMappingDraft(selections, MAPPING, MAPPING).reporterPath).toBeNull()
  })

  it('keeps the reporting party, its name and the period when their fields stay', () => {
    const selections = buildFieldSelections(FIELDS, MAPPING)

    expect(toMappingDraft(selections, MAPPING, MAPPING)).toMatchObject({
      reporterPath: 'nit',
      reporterNamePath: 'razon_social',
      periodPath: 'anio'
    })
  })
})

describe('keptPaths', () => {
  it('lists only the fields that survive the edit', () => {
    const selections = buildFieldSelections(FIELDS, null).map(selection =>
      selection.path === 'gmf' ? { ...selection, kept: false } : selection
    )

    expect(keptPaths(selections)).toEqual(new Set(['nit', 'razon_social', 'anio']))
  })
})

describe('configurationStatus', () => {
  it('reports a mapping without a reporting party as unusable', () => {
    const draft = toMappingDraft(
      [{ path: 'gmf', kept: true, conceptId: 'bank:cert_gmf_valor' }],
      NO_ROLES,
      null
    )

    expect(configurationStatus(draft)).toBe('unusable')
    expect(isDraftSavable(draft)).toBe(false)
  })

  it('reports a type with no mapped field as not mapped rather than broken', () => {
    const draft = toMappingDraft([{ path: 'gmf', kept: true, conceptId: null }], NO_ROLES, null)

    expect(configurationStatus(draft)).toBe('notMapped')
    expect(isDraftSavable(draft)).toBe(true)
  })

  it('reports a mapping with a reporting party and an entry as configured', () => {
    const draft = toMappingDraft(buildFieldSelections(FIELDS, MAPPING), MAPPING, MAPPING)

    expect(configurationStatus(draft)).toBe('configured')
  })
})

describe('shouldSaveDraft', () => {
  it('does not create an empty mapping for a type that never had one', () => {
    const draft = toMappingDraft([{ path: 'gmf', kept: true, conceptId: null }], NO_ROLES, null)

    expect(shouldSaveDraft(draft, null)).toBe(false)
  })

  it('sends an emptied draft for a type that had a mapping, so it gets cleared', () => {
    const draft = toMappingDraft([{ path: 'gmf', kept: true, conceptId: null }], NO_ROLES, MAPPING)

    expect(shouldSaveDraft(draft, MAPPING)).toBe(true)
  })
})

describe('mappingChangeSeverity', () => {
  function change(kind: string): MappingChange {
    return {
      kindId: 'exogena_dian',
      change: kind,
      path: 'gmf',
      fieldPath: 'gmf',
      conceptId: 'bank:cert_gmf_valor',
      reason: 'the schema no longer declares this field'
    }
  }

  it('treats losing the whole mapping as critical', () => {
    expect(mappingChangeSeverity(change('mapping_cleared'))).toBe('critical')
  })

  it('treats a mapping the server could not prune as critical', () => {
    expect(mappingChangeSeverity(change('prune_failed'))).toBe('critical')
  })

  it('treats a single dropped entry as an expected consequence', () => {
    expect(mappingChangeSeverity(change('entry_dropped'))).toBe('notice')
    expect(mappingChangeSeverity(change('path_cleared'))).toBe('notice')
  })
})
