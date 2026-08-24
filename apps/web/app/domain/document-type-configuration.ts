/**
 * Turning the configuration screen's choices into what the server stores.
 *
 * The screen edits two things that have to stay consistent with each other:
 * the extraction schema (which fields are asked of the OCR at all) and the
 * concept mapping (what those fields mean to a reconciliation model). Dropping
 * a field without dropping the mapping entry that pointed at it leaves a
 * mapping the server has to prune behind the user's back, so both sides are
 * derived here from one list of selections.
 */

import type {
  ConceptMapping,
  ConceptMappingDraft,
  ConceptMappingEntry,
  MappingChange
} from './entities/concept-mapping'
import type { SchemaField } from './extraction-schema'

/** One row of the field table: what the schema declares, plus what the user
 * decided about it. */
export interface FieldSelection {
  path: string
  /** False once the user asks for the field to be dropped from the schema. */
  kept: boolean
  /** Null is a legitimate answer: the field is still extracted, it just takes
   * no part in reconciliation. */
  conceptId: string | null
}

/** The three paths that are about the document as a whole rather than about
 * one figure it states. */
export interface MappingRoles {
  reporterPath: string | null
  reporterNamePath: string | null
  periodPath: string | null
}

export type ConfigurationStatus = 'unusable' | 'notMapped' | 'configured'

export type MappingChangeSeverity = 'critical' | 'notice'

/**
 * The starting state of the field table.
 *
 * Everything the schema declares starts kept, because the stored schema is
 * what the OCR is already extracting: this screen is a place to trim, not a
 * blank slate the user has to re-approve field by field.
 */
export function buildFieldSelections(
  fields: SchemaField[],
  mapping: ConceptMapping | null
): FieldSelection[] {
  const conceptByPath = new Map(
    (mapping?.entries ?? []).map(entry => [entry.fieldPath, entry.conceptId])
  )
  return fields.map(field => ({
    path: field.path,
    kept: true,
    conceptId: conceptByPath.get(field.path) ?? null
  }))
}

export function keptPaths(selections: readonly FieldSelection[]): Set<string> {
  return new Set(selections.filter(selection => selection.kept).map(selection => selection.path))
}

/**
 * The mapping to store for the selections as they stand.
 *
 * `accountPath` and `sign` are carried over from the entry that already
 * described the same field: they are curation this screen has no control for,
 * and rebuilding an entry from scratch would quietly flip a certificate that
 * was configured to state its figures with the opposite sign.
 */
export function toMappingDraft(
  selections: readonly FieldSelection[],
  roles: MappingRoles,
  existing: ConceptMapping | null
): ConceptMappingDraft {
  const kept = keptPaths(selections)
  const previousByPath = new Map((existing?.entries ?? []).map(entry => [entry.fieldPath, entry]))

  const entries: ConceptMappingEntry[] = selections
    .filter(selection => selection.kept && selection.conceptId)
    .map((selection) => {
      const previous = previousByPath.get(selection.path)
      return {
        fieldPath: selection.path,
        conceptId: selection.conceptId as string,
        // A trimmed field cannot name an account any more than it can carry an
        // amount, so a stale account path is dropped rather than sent back.
        accountPath: previous?.accountPath && kept.has(previous.accountPath)
          ? previous.accountPath
          : null,
        sign: previous?.sign ?? 1
      }
    })

  const rolePath = (path: string | null) => (path && kept.has(path) ? path : null)

  return {
    entries,
    reporterPath: rolePath(roles.reporterPath),
    reporterNamePath: rolePath(roles.reporterNamePath),
    periodPath: rolePath(roles.periodPath)
  }
}

/**
 * Whether the type actually reconciles anything.
 *
 * Entries without a reporter path are the trap this screen exists to close:
 * the server stores them happily and then discards every fact they produce,
 * so that state is reported as unusable rather than as configured.
 */
export function configurationStatus(draft: ConceptMappingDraft): ConfigurationStatus {
  if (draft.entries.length === 0) return 'notMapped'
  if (!draft.reporterPath) return 'unusable'
  return 'configured'
}

/** A mapping this screen would refuse to save, because saving it would make the
 * type look configured while producing nothing. */
export function isDraftSavable(draft: ConceptMappingDraft): boolean {
  return configurationStatus(draft) !== 'unusable'
}

/** Whether sending this draft is worth a request at all: an empty draft for a
 * type that was never mapped would only create an empty record. */
export function shouldSaveDraft(draft: ConceptMappingDraft, existing: ConceptMapping | null): boolean {
  if (existing) return true
  return draft.entries.length > 0 || draft.reporterPath !== null || draft.periodPath !== null
}

/**
 * How loudly a consequence of a schema edit has to be reported.
 *
 * `mapping_cleared` means the type stopped reconciling entirely and
 * `prune_failed` means the server could not tell what state the mapping is in;
 * both need the user back on this screen, whereas a single dropped entry is
 * the expected outcome of trimming a field.
 */
export function mappingChangeSeverity(change: MappingChange): MappingChangeSeverity {
  return change.change === 'mapping_cleared' || change.change === 'prune_failed'
    ? 'critical'
    : 'notice'
}
