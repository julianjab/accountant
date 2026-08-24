/**
 * What a document's extracted fields mean to the reconciliation.
 *
 * The document detail used to show only what the OCR read: a faithful copy of
 * the paper, in the paper's own words, with nothing saying which of those
 * figures the cross-check actually leans on. The configuration screen knows —
 * it is where the concepts were picked — but the person reviewing a client's
 * certificate is not on that screen, and had no way to tell a figure that
 * answers a line of the exogena from one that is merely transcribed.
 *
 * These rules turn a stored concept mapping back into rows: the field, what
 * the paper calls it, the concept it was mapped onto, and the line of the base
 * report it answers. The figures that answer one come first, because those are
 * the ones a mistake in shows up as a discrepancy.
 */

import type { ConceptMapping, ConceptMappingEntry } from '~/domain/entities/concept-mapping'
import type { DocumentTypeField } from '~/domain/entities/document-type'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import { labelFor } from '~/domain/field-sections'

/** One value a mapped path resolved to, with the account it belongs to when
 * the certificate details its accounts one per row. */
export interface MappedValue {
  value: unknown
  account: string | null
}

export interface MappedField {
  fieldPath: string
  /** What the document calls it, falling back to the path. */
  label: string
  conceptLabel: string
  /** The line of the base report this answers, null when nothing compares it. */
  spineLabel: string | null
  /** The document states this with the opposite sign to the concept. */
  inverted: boolean
  values: MappedValue[]
}

export interface MappedFieldGroups {
  /** Mapped onto a concept the base report also states, so it is compared. */
  crossed: MappedField[]
  /** Mapped, and read into the reconciliation, but nothing checks it. */
  uncrossed: MappedField[]
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

interface ResolvedValue {
  value: unknown
  /** The list positions walked to get here, so an amount and the account
   * number beside it on the same row can be paired back up. */
  indices: number[]
}

/**
 * Every value a dotted path reaches, `a[].b` walking each element of `a`.
 *
 * Mirrors what the server's projection does when it turns these same paths
 * into facts — a path that yields two amounts there has to show two figures
 * here, or the screen is describing a different document than the cross-check
 * read.
 */
export function resolvePath(fields: Record<string, unknown>, path: string): ResolvedValue[] {
  let current: ResolvedValue[] = [{ value: fields, indices: [] }]
  for (const segment of path.split('.')) {
    const iterate = segment.endsWith('[]')
    const key = iterate ? segment.slice(0, -2) : segment
    const next: ResolvedValue[] = []
    for (const node of current) {
      if (!isPlainObject(node.value)) continue
      const child = node.value[key]
      if (child === undefined || child === null) continue
      if (!iterate) {
        next.push({ value: child, indices: node.indices })
        continue
      }
      if (!Array.isArray(child)) continue
      child.forEach((item, index) => next.push({ value: item, indices: [...node.indices, index] }))
    }
    current = next
  }
  return current
}

/** The account beside an amount, matched by the list positions both were read
 * at — the same element-wise pairing the projection makes. */
function accountFor(
  fields: Record<string, unknown>,
  accountPath: string | null,
  indices: number[]
): string | null {
  if (!accountPath) return null
  const candidates = resolvePath(fields, accountPath)
  const sameRow = candidates.find(
    candidate => candidate.indices.length === 0 || sameIndices(candidate.indices, indices)
  )
  const value = sameRow?.value
  if (value === undefined || value === null || value === '') return null
  return String(value)
}

function sameIndices(a: number[], b: number[]): boolean {
  return a.length <= b.length && a.every((index, position) => index === b[position])
}

function conceptLabels(kind: ReconciliationKind | null): Map<string, string> {
  const labels = new Map<string, string>()
  for (const concept of kind?.evidenceConcepts ?? []) labels.set(concept.id, concept.label)
  for (const concept of kind?.spineConcepts ?? []) labels.set(concept.id, concept.label)
  return labels
}

function toMappedField(
  entry: ConceptMappingEntry,
  fields: Record<string, unknown>,
  described: readonly DocumentTypeField[],
  labels: Map<string, string>
): MappedField {
  return {
    fieldPath: entry.fieldPath,
    label: labelFor(entry.fieldPath, described),
    // The raw id is the last resort rather than a blank: a concept the kind
    // stopped publishing still has to name itself, or the row reads as mapped
    // onto nothing.
    conceptLabel: labels.get(entry.conceptId) ?? entry.conceptId,
    spineLabel: entry.spineConceptId
      ? (labels.get(entry.spineConceptId) ?? entry.spineConceptId)
      : null,
    inverted: entry.sign === -1,
    values: resolvePath(fields, entry.fieldPath).map(resolved => ({
      value: resolved.value,
      account: accountFor(fields, entry.accountPath, resolved.indices)
    }))
  }
}

/**
 * The mapped fields of one document, the compared ones first.
 *
 * A mapping entry with no value in this particular document is kept rather
 * than dropped: "the certificate should state this and does not" is the whole
 * point of the cross-check, and silently omitting the row would leave the
 * reader looking for a figure the screen decided not to mention.
 */
export function mappedFieldGroups(
  mapping: ConceptMapping | null,
  extractedFields: Record<string, unknown> | null,
  described: readonly DocumentTypeField[],
  kind: ReconciliationKind | null
): MappedFieldGroups {
  if (!mapping || !extractedFields) return { crossed: [], uncrossed: [] }
  const labels = conceptLabels(kind)
  const mapped = mapping.entries.map(entry =>
    toMappedField(entry, extractedFields, described, labels)
  )
  return {
    crossed: mapped.filter(field => field.spineLabel !== null),
    uncrossed: mapped.filter(field => field.spineLabel === null)
  }
}
