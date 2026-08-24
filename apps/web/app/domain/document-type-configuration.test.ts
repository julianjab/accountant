import type { MappingRoles, FieldSelection } from '~/domain/document-type-configuration'
import { describe, expect, it } from 'vitest'
import type { ConceptMapping, MappingChange } from '~/domain/entities/concept-mapping'
import type { FieldRole } from '~/domain/entities/document-type'
import type {
  DocumentTypeProposal,
  ProposedField
} from '~/domain/entities/document-type-proposal'
import type { SchemaField } from '~/domain/extraction-schema'
import {
  buildFieldSelections,
  buildProposalRows,
  configurationStatus,
  creationBlock,
  groupBySection,
  invalidTaxYears,
  isDraftSavable,
  keptPaths,
  fieldsMissingAccountPath,
  groupBySpineConcept,
  mappingChangeSeverity,
  parseTaxYears,
  proposalMappingBaseline,
  shouldSaveDraft,
  toDocumentTypeFields,
  toMappingDraft,
  toProposedFieldMappings
} from '~/domain/document-type-configuration'

function field(path: string): SchemaField {
  return { path, name: path, type: 'string', description: '', required: false }
}

const FIELDS: SchemaField[] = [field('nit'), field('razon_social'), field('anio'), field('gmf')]

const MAPPING: ConceptMapping = {
  documentTypeId: 'dt-1',
  kindId: 'exogena_dian',
  entries: [
    {
      fieldPath: 'gmf',
      conceptId: 'bank:cert_gmf_valor',
      accountPath: 'nit',
      sign: -1,
      spineConceptId: 'dian:gmf',
      perAccount: true
    }
  ],
  reporterPath: 'nit',
  reporterNamePath: 'razon_social',
  periodPath: 'anio',
  reporterTaxId: null,
  reporterName: null,
  period: null
}

const NO_ROLES: MappingRoles = {
  reporterPath: null,
  reporterNamePath: null,
  periodPath: null,
  reporterTaxId: null,
  reporterName: null,
  period: null
}

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
      {
        fieldPath: 'gmf',
        conceptId: 'bank:cert_gmf_valor',
        accountPath: null,
        sign: 1,
        spineConceptId: null,
        perAccount: false
      }
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
      periodPath: 'anio',
      reporterTaxId: null,
      reporterName: null,
      period: null
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

describe('toMappingDraft, spine line and comparison', () => {
  function selection(overrides: Partial<FieldSelection> & { path: string }): FieldSelection {
    return {
      kept: true,
      conceptId: 'bank:cert_gmf_valor',
      spineConceptId: null,
      perAccount: false,
      accountPath: null,
      ...overrides
    }
  }

  it('stores the line of the base report the field answers', () => {
    const draft = toMappingDraft(
      [selection({ path: 'gmf', spineConceptId: 'dian:gmf' })],
      { ...NO_ROLES, reporterPath: 'nit' },
      null
    )

    expect(draft.entries[0]).toMatchObject({ spineConceptId: 'dian:gmf' })
  })

  it('lets several fields answer the same line, so the engine sums them', () => {
    const draft = toMappingDraft(
      [
        selection({ path: 'capital', spineConceptId: 'dian:deuda' }),
        selection({ path: 'intereses', spineConceptId: 'dian:deuda' })
      ],
      { ...NO_ROLES, reporterPath: 'nit' },
      null
    )

    expect(draft.entries.map(entry => entry.spineConceptId)).toEqual([
      'dian:deuda',
      'dian:deuda'
    ])
  })

  it('compares account by account when the document names the account', () => {
    const draft = toMappingDraft(
      [
        selection({ path: 'cuentas[].saldo', perAccount: true, accountPath: 'cuentas[].numero' }),
        selection({ path: 'cuentas[].numero', conceptId: null })
      ],
      { ...NO_ROLES, reporterPath: 'nit' },
      null
    )

    expect(draft.entries[0]).toMatchObject({
      perAccount: true,
      accountPath: 'cuentas[].numero'
    })
  })

  it('falls back to a total when no field names the account', () => {
    const draft = toMappingDraft(
      [selection({ path: 'saldo', perAccount: true })],
      { ...NO_ROLES, reporterPath: 'nit' },
      null
    )

    // Comparing per account with nothing to pair against would report a figure
    // the certificate does state as missing.
    expect(draft.entries[0]).toMatchObject({ perAccount: false, accountPath: null })
  })

  it('drops the per-account comparison when the account field is trimmed away', () => {
    const draft = toMappingDraft(
      [
        selection({ path: 'cuentas[].saldo', perAccount: true, accountPath: 'cuentas[].numero' }),
        selection({ path: 'cuentas[].numero', kept: false, conceptId: null })
      ],
      { ...NO_ROLES, reporterPath: 'nit' },
      null
    )

    expect(draft.entries[0]).toMatchObject({ perAccount: false, accountPath: null })
  })

  it('keeps stored curation a caller did not touch', () => {
    const draft = toMappingDraft(
      [
        { path: 'gmf', kept: true, conceptId: 'bank:cert_gmf_valor' },
        { path: 'nit', kept: true, conceptId: null }
      ],
      MAPPING,
      MAPPING
    )

    expect(draft.entries[0]).toMatchObject({
      spineConceptId: 'dian:gmf',
      perAccount: true,
      accountPath: 'nit',
      sign: -1
    })
  })

  it('lets the user clear the line a field used to answer', () => {
    const draft = toMappingDraft(
      [selection({ path: 'gmf', spineConceptId: null }), selection({ path: 'nit', conceptId: null })],
      MAPPING,
      MAPPING
    )

    expect(draft.entries[0]).toMatchObject({ spineConceptId: null })
  })
})

describe('groupBySpineConcept', () => {
  const CAPITAL = { path: 'capital', kept: true, conceptId: 'c', spineConceptId: 'dian:deuda' }
  const INTERES = { path: 'intereses', kept: true, conceptId: 'c', spineConceptId: 'dian:deuda' }
  const GMF = { path: 'gmf', kept: true, conceptId: 'c', spineConceptId: 'dian:gmf' }

  it('flags the line several fields feed as a sum', () => {
    const [deuda, gmf] = groupBySpineConcept([CAPITAL, INTERES, GMF])

    expect(deuda).toMatchObject({ spineConceptId: 'dian:deuda', paths: ['capital', 'intereses'], summed: true })
    expect(gmf).toMatchObject({ summed: false })
  })

  it('gathers everything that answers no line, last', () => {
    const groups = groupBySpineConcept([
      { path: 'nit', kept: true, conceptId: null },
      CAPITAL,
      { path: 'notas', kept: false, conceptId: 'c', spineConceptId: 'dian:deuda' }
    ])

    expect(groups.at(-1)).toMatchObject({ spineConceptId: null, paths: ['nit', 'notas'] })
  })

  it('flags a line summing a per-account figure with a total', () => {
    const groups = groupBySpineConcept([
      { ...CAPITAL, perAccount: true, accountPath: 'cuentas[].numero' },
      { ...INTERES, perAccount: false }
    ])

    expect(groups[0]).toMatchObject({ mixedComparison: true })
  })
})

describe('fieldsMissingAccountPath', () => {
  it('names the field that claims a per-account comparison with no account', () => {
    expect(
      fieldsMissingAccountPath([
        { path: 'saldo', kept: true, conceptId: 'c', spineConceptId: 's', perAccount: true, accountPath: null },
        { path: 'gmf', kept: true, conceptId: 'c', spineConceptId: 's', perAccount: false, accountPath: null }
      ])
    ).toEqual(['saldo'])
  })

  // Regression: the screen only shows the total/per-account question (and the account-path
  // control) once a spine concept is chosen, so a selection stuck with perAccount: true and no
  // spineConceptId — e.g. the user answered it, then cleared the spine concept — has no control
  // left to fix it. It must not be flagged, or the warning it drives would be stuck forever.
  it('does not flag a field with no spine concept, even if perAccount was left true', () => {
    expect(
      fieldsMissingAccountPath([
        { path: 'saldo', kept: true, conceptId: 'c', spineConceptId: null, perAccount: true, accountPath: null }
      ])
    ).toEqual([])
  })
})

function proposedField(
  path: string,
  role: FieldRole,
  section = 'Datos del titular'
): ProposedField {
  return { path, label: path.toUpperCase(), role, sampleValue: '1', section }
}

const PROPOSAL: DocumentTypeProposal = {
  extractionPrompt: 'Extract it',
  extractionSchema: {
    type: 'object',
    properties: {
      nit: { type: 'string' },
      razon_social: { type: 'string' },
      gmf: { type: 'number' },
      pie_de_pagina: { type: 'string' }
    }
  },
  fields: [
    proposedField('nit', 'identifier'),
    proposedField('razon_social', 'context'),
    proposedField('gmf', 'amount', 'Gravamen a los movimientos financieros'),
    proposedField('pie_de_pagina', 'context', '')
  ],
  fieldMappings: [
    { fieldPath: 'gmf', conceptId: 'bank:gmf', accountPath: null, sign: -1 }
  ],
  unmappedFields: [{ fieldPath: 'pie_de_pagina', reason: 'not an amount' }],
  kindId: 'exogena_dian',
  reporterPath: 'nit',
  reporterNamePath: 'razon_social',
  periodPath: null
}

describe('buildProposalRows', () => {
  it('starts the identification and the amounts selected, and the rest unselected', () => {
    const rows = buildProposalRows(PROPOSAL, [])

    expect(rows.map(row => [row.path, row.kept])).toEqual([
      ['nit', true],
      ['razon_social', false],
      ['gmf', true],
      ['pie_de_pagina', false]
    ])
  })

  it('carries the proposed concept and sign onto the row', () => {
    const rows = buildProposalRows(PROPOSAL, [])

    expect(rows.find(row => row.path === 'gmf')).toMatchObject({
      conceptId: 'bank:gmf',
      label: 'GMF',
      section: 'Gravamen a los movimientos financieros'
    })
  })

  it('lists a schema field the proposal never described, and keeps it', () => {
    const rows = buildProposalRows(PROPOSAL, [
      field('nit'),
      { path: 'sucursal', name: 'sucursal', type: 'string', description: '', required: false }
    ])

    expect(rows.find(row => row.path === 'sucursal')).toMatchObject({
      kept: true,
      section: null
    })
  })
})

describe('groupBySection', () => {
  it('keeps the document order and leaves the headless fields last', () => {
    const groups = groupBySection(buildProposalRows(PROPOSAL, []))

    expect(groups.map(group => group.section)).toEqual([
      'Datos del titular',
      'Gravamen a los movimientos financieros',
      null
    ])
    expect(groups[0]).toMatchObject({ paths: ['nit', 'razon_social'], keptCount: 1 })
  })
})

describe('creationBlock', () => {
  const roles: MappingRoles = { ...NO_ROLES, reporterPath: 'nit' }

  it('lets a draft through when the reporting party is kept', () => {
    const rows = buildProposalRows(PROPOSAL, [])
    const draft = toMappingDraft(rows, roles, proposalMappingBaseline(PROPOSAL))

    expect(creationBlock(rows, draft)).toBeNull()
    // The proposal's sign is curation this screen has no control for, so it
    // has to survive the trimming.
    expect(draft.entries[0]).toMatchObject({ fieldPath: 'gmf', sign: -1 })
  })

  it('blocks when the field holding the tax id ends up unselected', () => {
    const rows = buildProposalRows(PROPOSAL, []).map(row =>
      row.path === 'nit' ? { ...row, kept: false } : row
    )
    const draft = toMappingDraft(rows, roles, proposalMappingBaseline(PROPOSAL))

    expect(creationBlock(rows, draft)).toBe('noReporter')
  })

  it('blocks a type that would extract nothing', () => {
    const rows = buildProposalRows(PROPOSAL, []).map(row => ({ ...row, kept: false }))
    const draft = toMappingDraft(rows, roles, proposalMappingBaseline(PROPOSAL))

    expect(creationBlock(rows, draft)).toBe('noFields')
  })

  it('allows a type nobody mapped to a concept', () => {
    const rows = buildProposalRows({ ...PROPOSAL, fieldMappings: [] }, [])
    const draft = toMappingDraft(
      rows,
      NO_ROLES,
      null
    )

    expect(creationBlock(rows, draft)).toBeNull()
  })
})

describe('toDocumentTypeFields', () => {
  it('stores the label, role and section of the fields that were kept', () => {
    const rows = buildProposalRows(PROPOSAL, [])

    expect(toDocumentTypeFields(rows)).toEqual([
      { path: 'nit', label: 'NIT', role: 'identifier', section: 'Datos del titular' },
      {
        path: 'gmf',
        label: 'GMF',
        role: 'amount',
        section: 'Gravamen a los movimientos financieros'
      }
    ])
  })

  it('describes a headless field with an empty section rather than dropping it', () => {
    const rows = buildProposalRows(PROPOSAL, []).map(row =>
      row.path === 'pie_de_pagina' ? { ...row, kept: true } : row
    )

    expect(toDocumentTypeFields(rows)).toContainEqual({
      path: 'pie_de_pagina',
      label: 'PIE_DE_PAGINA',
      role: 'context',
      section: ''
    })
  })
})

describe('toProposedFieldMappings', () => {
  it('sends only the fields that survived the trimming', () => {
    const rows = buildProposalRows(PROPOSAL, []).map(row =>
      row.path === 'gmf' ? { ...row, kept: false } : row
    )
    const draft = toMappingDraft(
      rows,
      { ...NO_ROLES, reporterPath: 'nit' },
      proposalMappingBaseline(PROPOSAL)
    )

    expect(toProposedFieldMappings(draft)).toEqual([])
  })
})

describe('parseTaxYears', () => {
  it('reads an empty box as "any year"', () => {
    expect(parseTaxYears('   ')).toEqual([])
  })

  it('reads years separated by commas or spaces, deduplicated and sorted', () => {
    expect(parseTaxYears('2025, 2024 2025')).toEqual([2024, 2025])
  })

  it('reports what is not a year instead of dropping it', () => {
    expect(invalidTaxYears('2024, veinticuatro, 24')).toEqual(['veinticuatro', '24'])
    expect(parseTaxYears('2024, veinticuatro, 24')).toEqual([2024])
  })
})

describe('a type that declares what its documents never state', () => {
  const entry = { path: 'gmf', kept: true, conceptId: 'bank:cert_gmf_valor' }

  it('counts as configured when the type declares who reports', () => {
    // The certificate never prints its issuer, so no path can answer this and
    // the mapping would otherwise read as unusable forever.
    const draft = toMappingDraft([entry], { ...NO_ROLES, reporterTaxId: '890903938' }, null)

    expect(configurationStatus(draft)).toBe('configured')
    expect(isDraftSavable(draft)).toBe(true)
  })

  it('is still unusable when neither the paper nor the type names anyone', () => {
    const draft = toMappingDraft([entry], NO_ROLES, null)

    expect(configurationStatus(draft)).toBe('unusable')
  })

  it('reads an emptied input as not declared, not as declared blank', () => {
    const draft = toMappingDraft([entry], { ...NO_ROLES, reporterTaxId: '   ' }, null)

    expect(draft.reporterTaxId).toBeNull()
    expect(configurationStatus(draft)).toBe('unusable')
  })

  it('keeps a declared value even though no kept field backs it', () => {
    // Declared values are not read from the document, so trimming the schema
    // cannot invalidate them the way it invalidates a path.
    const draft = toMappingDraft(
      [{ ...entry, kept: false }],
      { ...NO_ROLES, reporterTaxId: '890903938', period: '2025' },
      null
    )

    expect(draft.reporterTaxId).toBe('890903938')
    expect(draft.period).toBe('2025')
  })
})
