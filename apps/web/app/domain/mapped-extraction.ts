/**
 * What each extracted value means to the reconciliation.
 *
 * The document detail used to show only what the OCR read: a faithful copy of
 * the paper, in the paper's own words, with nothing saying which of those
 * figures the cross-check leans on. The concepts were picked on the type's
 * configuration screen, which is not where anyone reviews a client's
 * certificate.
 *
 * These rules turn a stored concept mapping into a lookup by field path, so
 * the value rows can carry that answer themselves — a tag beside the figure,
 * where the reader already is, rather than a second list of the same document
 * somewhere above.
 */

import type { ConceptMapping } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'

export interface MappedConcept {
  conceptLabel: string
  /** The line of the base report this answers, null when nothing compares it. */
  spineLabel: string | null
  /** The document states this with the opposite sign to the concept. */
  inverted: boolean
}

function conceptLabels(kind: ReconciliationKind | null): Map<string, string> {
  const labels = new Map<string, string>()
  for (const concept of kind?.evidenceConcepts ?? []) labels.set(concept.id, concept.label)
  for (const concept of kind?.spineConcepts ?? []) labels.set(concept.id, concept.label)
  return labels
}

/**
 * Every mapped field of a document type, keyed by the path it sits at.
 *
 * The keys are the mapping's own paths (`obligaciones_a_cargo[].capital`),
 * which is the same shape the value tree rebuilds as it walks — that is what
 * lets a leaf several levels down find its own concept without anything
 * threading context through the render.
 */
export function conceptsByPath(
  mapping: ConceptMapping | null,
  kind: ReconciliationKind | null
): Map<string, MappedConcept> {
  const labels = conceptLabels(kind)
  const byPath = new Map<string, MappedConcept>()
  for (const entry of mapping?.entries ?? []) {
    byPath.set(entry.fieldPath, {
      // The raw id is the last resort rather than a blank: a concept the kind
      // stopped publishing still has to name itself, or the tag reads as
      // mapped onto nothing.
      conceptLabel: labels.get(entry.conceptId) ?? entry.conceptId,
      spineLabel: entry.spineConceptId
        ? (labels.get(entry.spineConceptId) ?? entry.spineConceptId)
        : null,
      inverted: entry.sign === -1
    })
  }
  return byPath
}

/** The path a nested value sits at, in the mapping's own notation. */
export function childPath(parentPath: string, key: string, insideList: boolean): string {
  if (!parentPath) return key
  return insideList ? `${parentPath}[].${key}` : `${parentPath}.${key}`
}
