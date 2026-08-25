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
  withRowWordings,
  setRowLabelPath,
  blockLabelPaths,
  addRow,
  removeRow,
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
      perAccount: true,
      rowLabelPath: null,
      rowLabel: null
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
        perAccount: false,
        rowLabelPath: null,
        rowLabel: null
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
      rowLabelPath: null,
      rowLabel: null,
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

    expect(deuda).toMatchObject({ spineConceptId: 'dian:deuda', keys: ['capital', 'intereses'], summed: true })
    expect(gmf).toMatchObject({ summed: false })
  })

  it('gathers everything that answers no line, last', () => {
    const groups = groupBySpineConcept([
      { path: 'nit', kept: true, conceptId: null },
      CAPITAL,
      { path: 'notas', kept: false, conceptId: 'c', spineConceptId: 'dian:deuda' }
    ])

    expect(groups.at(-1)).toMatchObject({ spineConceptId: null, keys: ['nit', 'notas'] })
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
  it('stores the label, role, section and sample value of the fields kept', () => {
    const rows = buildProposalRows(PROPOSAL, [])

    expect(toDocumentTypeFields(rows, { keptOnly: true })).toEqual([
      {
        path: 'nit',
        label: 'NIT',
        role: 'identifier',
        section: 'Datos del titular',
        sampleValue: '1'
      },
      {
        path: 'gmf',
        label: 'GMF',
        role: 'amount',
        section: 'Gravamen a los movimientos financieros',
        sampleValue: '1'
      }
    ])
  })

  it('describes a headless field with an empty section rather than dropping it', () => {
    const rows = buildProposalRows(PROPOSAL, []).map(row =>
      row.path === 'pie_de_pagina' ? { ...row, kept: true } : row
    )

    expect(toDocumentTypeFields(rows, { keptOnly: true })).toContainEqual({
      path: 'pie_de_pagina',
      label: 'PIE_DE_PAGINA',
      role: 'context',
      section: '',
      sampleValue: '1'
    })
  })

  it('describes every field the reading identified, ticked or not', () => {
    // The unticked ones stay in the type's candidate schema so they can be
    // ticked back later, and a field can only be offered to someone by name.
    const rows = buildProposalRows(PROPOSAL, [])

    const described = toDocumentTypeFields(rows).map(field => field.path)

    expect(described).toEqual(rows.map(row => row.path))
    expect(described.length).toBeGreaterThan(
      toDocumentTypeFields(rows, { keptOnly: true }).length
    )
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

describe('buildProposalRows when the proposal describes nothing', () => {
  // What actually happens: `fields` is optional to the model and it omits it.
  const BARE = { ...PROPOSAL, fields: [], fieldMappings: [] }

  const SCHEMA_FIELDS = [
    { path: 'issuer_nit', name: 'issuer_nit', type: 'string', description: 'NIT of the issuing entity', required: true },
    { path: 'issuer_city', name: 'issuer_city', type: 'string', description: '', required: false },
    { path: 'saldos.cuenta_ahorros', name: 'cuenta_ahorros', type: 'number', description: '', required: false }
  ]

  it('names a field with what the schema says it is, not its path', () => {
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.find(r => r.path === 'issuer_nit')!.label).toBe('NIT of the issuing entity')
  })

  it('falls back to the property name when the schema describes nothing either', () => {
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.find(r => r.path === 'issuer_city')!.label).toBe('issuer_city')
  })

  it('reads a numeric field as an amount, so the figures are told from the letterhead', () => {
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.find(r => r.path === 'saldos.cuenta_ahorros')!.role).toBe('amount')
  })

  it('reads a field named after a tax or account number as an identifier', () => {
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.find(r => r.path === 'issuer_nit')!.role).toBe('identifier')
  })

  it('groups a nested field under the object that contains it', () => {
    // The schema's own nesting is the document's grouping, recorded without
    // anyone having been asked for it.
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.find(r => r.path === 'saldos.cuenta_ahorros')!.section).toBe('saldos')
  })

  it('starts the figures and the identification ticked and the rest not', () => {
    const rows = buildProposalRows(BARE, SCHEMA_FIELDS)

    expect(rows.filter(r => r.kept).map(r => r.path)).toEqual([
      'issuer_nit',
      'saldos.cuenta_ahorros'
    ])
  })
})

/* ------------------------------------------------------------------ *
 * A block the document prints as a table
 *
 * An employment certificate states sixteen income lines in one repeated
 * block. One answer for `ingresos[].valor` files all sixteen under one
 * concept; these pin that each row becomes its own row of the list instead.
 * ------------------------------------------------------------------ */

describe('a table, listed row by row', () => {
  const SALARIOS = 'payroll:cert_pagos_salarios'
  const CESANTIAS = 'payroll:cert_cesantias_consignadas'
  const VALOR = 'ingresos[].valor'
  const CONCEPTO = 'ingresos[].concepto'
  const ROLES = { ...NO_ROLES, reporterPath: 'nit' }

  const WORDINGS = ['Pagos por salarios', 'Cesantías al fondo', 'Pagos por viáticos']
  const wordingsFor = (path: string) => (path === CONCEPTO ? WORDINGS : [])

  function entry(overrides: Partial<FieldSelection> & { path: string }): FieldSelection {
    return {
      rowLabel: null,
      kept: true,
      conceptId: null,
      spineConceptId: null,
      perAccount: false,
      accountPath: null,
      rowLabelPath: null,
      ...overrides
    }
  }

  /** The block as the screen holds it once someone says its rows differ. */
  function table(): FieldSelection[] {
    return setRowLabelPath(
      [entry({ path: CONCEPTO }), entry({ path: VALOR })],
      VALOR,
      CONCEPTO,
      wordingsFor
    )
  }

  function answered(): FieldSelection[] {
    return table().map((selection) => {
      if (selection.rowLabel === 'Pagos por salarios') {
        return { ...selection, conceptId: SALARIOS, spineConceptId: 'dian:pagos-salarios' }
      }
      if (selection.rowLabel === 'Cesantías al fondo') {
        return { ...selection, conceptId: CESANTIAS }
      }
      return selection
    })
  }

  it('lists every row the paper printed as a peer of the fields', () => {
    expect(table().map(selection => [selection.path, selection.rowLabel])).toEqual([
      [CONCEPTO, null],
      [VALOR, null],
      [VALOR, 'Pagos por salarios'],
      [VALOR, 'Cesantías al fondo'],
      [VALOR, 'Pagos por viáticos']
    ])
  })

  it('stores one entry per answered row, all on the same path', () => {
    const draft = toMappingDraft(answered(), ROLES, null)

    expect(draft.entries.map(e => [e.fieldPath, e.rowLabel, e.conceptId])).toEqual([
      [VALOR, 'Pagos por salarios', SALARIOS],
      [VALOR, 'Cesantías al fondo', CESANTIAS]
    ])
    expect(draft.entries[0]!.rowLabelPath).toBe(CONCEPTO)
  })

  it('never sends the field itself once its rows are the answers', () => {
    // One entry for `ingresos[].valor` with no row would claim all sixteen
    // lines at once — the exact misreading this whole shape exists to prevent.
    const draft = toMappingDraft(answered(), ROLES, null)

    expect(draft.entries.every(e => e.rowLabel !== null)).toBe(true)
  })

  it('leaves a row nobody answered out, rather than sweeping it into a neighbour', () => {
    const draft = toMappingDraft(answered(), ROLES, null)

    expect(draft.entries.map(e => e.rowLabel)).not.toContain('Pagos por viáticos')
  })

  it('keeps each row answering its own line of the base report', () => {
    const draft = toMappingDraft(answered(), ROLES, null)

    expect(draft.entries.map(e => e.spineConceptId)).toEqual(['dian:pagos-salarios', null])
  })

  it('drops the whole table once the field naming its rows is trimmed away', () => {
    const trimmed = answered().map(selection =>
      selection.path === CONCEPTO ? { ...selection, kept: false } : selection
    )

    expect(toMappingDraft(trimmed, ROLES, null).entries).toEqual([])
  })

  it('counts a row out of the schema, which reads the whole array or none of it', () => {
    expect([...keptPaths(answered())]).toEqual([CONCEPTO, VALOR])
  })

  it('goes back to one mapping for the block when the rows turn out to be alike', () => {
    const flattened = setRowLabelPath(answered(), VALOR, null, wordingsFor)

    expect(flattened.every(selection => selection.rowLabel === null)).toBe(true)
    expect(flattened.find(s => s.path === VALOR)!.rowLabelPath).toBeNull()
  })

  it('reads stored per-row entries back as rows of the list', () => {
    const mapping: ConceptMapping = {
      ...MAPPING,
      entries: [
        {
          fieldPath: VALOR,
          conceptId: SALARIOS,
          accountPath: null,
          sign: 1,
          spineConceptId: 'dian:pagos-salarios',
          perAccount: false,
          rowLabelPath: CONCEPTO,
          rowLabel: 'Pagos por salarios'
        },
        {
          fieldPath: VALOR,
          conceptId: CESANTIAS,
          accountPath: null,
          sign: 1,
          spineConceptId: null,
          perAccount: false,
          rowLabelPath: CONCEPTO,
          rowLabel: 'Cesantías al fondo'
        }
      ]
    }

    const selections = buildFieldSelections([field(VALOR)], mapping)

    expect(selections.map(s => [s.rowLabel, s.conceptId])).toEqual([
      [null, null],
      ['Pagos por salarios', SALARIOS],
      ['Cesantías al fondo', CESANTIAS]
    ])
    // The table has no single concept, and offering one would contradict its rows.
    expect(selections[0]!.rowLabelPath).toBe(CONCEPTO)
  })

  it('adds up the rows of one table that answer the same line', () => {
    const both = table().map(selection =>
      selection.rowLabel === null
        ? selection
        : { ...selection, conceptId: CESANTIAS, spineConceptId: 'dian:cesantias' }
    )

    const groups = groupBySpineConcept(both)

    expect(groups[0]).toMatchObject({ spineConceptId: 'dian:cesantias', summed: true })
    expect(groups[0]!.keys).toHaveLength(3)
  })
})

describe('withRowWordings', () => {
  const CONCEPTO = 'ingresos[].concepto'
  const VALOR = 'ingresos[].valor'

  function table(rows: { rowLabel: string, conceptId: string | null }[]): FieldSelection[] {
    const base = {
      kept: true,
      conceptId: null,
      spineConceptId: null,
      perAccount: false,
      accountPath: null
    }
    return [
      { ...base, path: VALOR, rowLabel: null, rowLabelPath: CONCEPTO },
      ...rows.map(row => ({ ...base, ...row, path: VALOR, rowLabelPath: null }))
    ]
  }

  it('offers every row the paper printed that nobody has answered yet', () => {
    const merged = withRowWordings(
      table([{ rowLabel: 'Pagos por salarios', conceptId: 'payroll:x' }]),
      () => ['Pagos por salarios', 'Pagos por viáticos']
    )

    expect(merged.map(s => [s.rowLabel, s.conceptId])).toEqual([
      [null, null],
      ['Pagos por salarios', 'payroll:x'],
      ['Pagos por viáticos', null]
    ])
  })

  it('keeps an answer for a row this sample happened not to print', () => {
    const merged = withRowWordings(
      table([{ rowLabel: 'Pagos por comisiones', conceptId: 'payroll:x' }]),
      () => []
    )

    expect(merged.map(s => s.rowLabel)).toEqual([null, 'Pagos por comisiones'])
  })

  it('does not ask twice for a row worded differently from the answer given', () => {
    const merged = withRowWordings(
      table([{ rowLabel: 'Auxilio de cesantía', conceptId: 'payroll:x' }]),
      () => ['AUXILIO DE  CESANTIA']
    )

    expect(merged).toHaveLength(2)
  })
})

describe('the column that names the rows', () => {
  const VALOR = 'ingresos[].valor'
  const CONCEPTO = 'ingresos[].concepto'
  const ROLES = { ...NO_ROLES, reporterPath: 'nit' }

  function block(): FieldSelection[] {
    const base = {
      kept: true,
      spineConceptId: null,
      perAccount: false,
      accountPath: null,
      rowLabel: null
    }
    return setRowLabelPath(
      [
        // Answered before anyone said the block was a table, which is the
        // state this comes out of: the label column had a concept of its own.
        { ...base, path: CONCEPTO, conceptId: 'payroll:cert_otros_pagos', rowLabelPath: null },
        { ...base, path: VALOR, conceptId: null, rowLabelPath: null }
      ],
      VALOR,
      CONCEPTO,
      () => ['Pagos por salarios']
    )
  }

  it('is recognised as the block\'s label, so the screen can stop offering it', () => {
    expect([...blockLabelPaths(block())]).toEqual([CONCEPTO])
  })

  it('is never mapped as a figure, however it was answered before', () => {
    // The projection would be asked to read an amount off a column of words.
    const draft = toMappingDraft(block(), ROLES, null)

    expect(draft.entries.map(entry => entry.fieldPath)).not.toContain(CONCEPTO)
  })

  it('stays in the schema, because matching each row needs it', () => {
    expect(keptPaths(block()).has(CONCEPTO)).toBe(true)
  })
})

describe('adding a row by hand', () => {
  const VALOR = 'ingresos[].valor'
  const CONCEPTO = 'ingresos[].concepto'

  function table(wordings: string[] = []): FieldSelection[] {
    const base = {
      kept: true,
      conceptId: null,
      spineConceptId: null,
      perAccount: false,
      accountPath: null,
      rowLabel: null
    }
    return setRowLabelPath(
      [{ ...base, path: CONCEPTO, rowLabelPath: null }, { ...base, path: VALOR, rowLabelPath: null }],
      VALOR,
      CONCEPTO,
      () => wordings
    )
  }

  it('gives a type whose sample was never read a way to answer at all', () => {
    // Without this the screen is a dead end: "each row is different", no rows.
    const added = addRow(table(), VALOR, 'Pagos por salarios')

    expect(added.map(selection => selection.rowLabel)).toEqual([null, null, 'Pagos por salarios'])
  })

  it('puts a hand-typed row alongside the ones read from the paper', () => {
    const added = addRow(table(['Pagos por salarios']), VALOR, 'Pagos por comisiones')

    expect(added.filter(s => s.rowLabel !== null).map(s => s.rowLabel)).toEqual([
      'Pagos por salarios',
      'Pagos por comisiones'
    ])
  })

  it('refuses a row the table already has, however it was typed', () => {
    const added = addRow(table(['Auxilio de cesantía']), VALOR, 'AUXILIO DE  CESANTIA ')

    expect(added.filter(s => s.rowLabel !== null)).toHaveLength(1)
  })

  it('refuses a blank wording, which would match every row nobody named', () => {
    expect(addRow(table(), VALOR, '   ').filter(s => s.rowLabel !== null)).toEqual([])
  })

  it('refuses a row on a field that is not a table', () => {
    const plain: FieldSelection[] = [
      {
        path: 'gmf',
        rowLabel: null,
        kept: true,
        conceptId: null,
        spineConceptId: null,
        perAccount: false,
        accountPath: null,
        rowLabelPath: null
      }
    ]

    expect(addRow(plain, 'gmf', 'Lo que sea')).toEqual(plain)
  })

  it('takes a row back off, along with the answer it held', () => {
    const removed = removeRow(table(['Pagos por salarios']), VALOR, 'Pagos por salarios')

    expect(removed.filter(s => s.rowLabel !== null)).toEqual([])
  })
})
