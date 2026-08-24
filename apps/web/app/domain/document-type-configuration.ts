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
  /** Which line of the base report this figure answers; null means it is
   * extracted but compared against nothing. */
  spineConceptId: string | null
  /** True when the document details each account, so the comparison is made
   * account by account instead of on the reporting party's total. */
  perAccount: boolean
  /** The field carrying the account number, without which there is no account
   * to pair against. */
  accountPath: string | null
}

/**
 * A row as the screen may hand it back before every choice has been made.
 *
 * The three reconciliation-specific choices are optional because leaving one
 * out has to mean "unchanged", not "cleared": a caller that only edits the
 * concept must not silently drop curation it never showed.
 */
export type FieldSelectionInput
  = Pick<FieldSelection, 'path' | 'kept' | 'conceptId'>
    & Partial<Omit<FieldSelection, 'path' | 'kept' | 'conceptId'>>

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
  const entryByPath = new Map((mapping?.entries ?? []).map(entry => [entry.fieldPath, entry]))
  return fields.map((field) => {
    const entry = entryByPath.get(field.path)
    return {
      path: field.path,
      kept: true,
      conceptId: entry?.conceptId ?? null,
      spineConceptId: entry?.spineConceptId ?? null,
      perAccount: entry?.perAccount ?? false,
      accountPath: entry?.accountPath ?? null
    }
  })
}

export function keptPaths(selections: readonly FieldSelectionInput[]): Set<string> {
  return new Set(selections.filter(selection => selection.kept).map(selection => selection.path))
}

/** An answer the screen did not give falls back to what was already stored, so
 * a control the screen never showed cannot clear curation behind the user. */
function chosen<T>(explicit: T | undefined, previous: T | undefined, fallback: T): T {
  if (explicit !== undefined) return explicit
  return previous ?? fallback
}

/**
 * The mapping to store for the selections as they stand.
 *
 * `sign` is carried over from the entry that already described the same field:
 * it is curation this screen has no control for, and rebuilding an entry from
 * scratch would quietly flip a certificate configured to state its figures with
 * the opposite sign.
 */
export function toMappingDraft(
  selections: readonly FieldSelectionInput[],
  roles: MappingRoles,
  existing: ConceptMapping | null
): ConceptMappingDraft {
  const kept = keptPaths(selections)
  const previousByPath = new Map((existing?.entries ?? []).map(entry => [entry.fieldPath, entry]))

  const entries: ConceptMappingEntry[] = selections
    .filter(selection => selection.kept && selection.conceptId)
    .map((selection) => {
      const previous = previousByPath.get(selection.path)
      const claimed = chosen(selection.accountPath, previous?.accountPath, null)
      // A trimmed field cannot name an account any more than it can carry an
      // amount, so a stale account path is dropped rather than sent back.
      const accountPath = claimed && kept.has(claimed) ? claimed : null
      return {
        fieldPath: selection.path,
        conceptId: selection.conceptId as string,
        accountPath,
        sign: previous?.sign ?? 1,
        spineConceptId: chosen(selection.spineConceptId, previous?.spineConceptId, null),
        // Comparing account by account when this side names no account pairs
        // every certified figure against nothing, which reports a figure the
        // document does state as missing. A total is the answer that at least
        // compares something.
        perAccount: chosen(selection.perAccount, previous?.perAccount, false) && accountPath !== null
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

/**
 * The fields answering one line of the base report.
 *
 * Grouping is the whole point of the spine choice: the engine adds up every
 * amount mapped to the same line before comparing it, which is how a debt the
 * base report states once and the certificate splits into capital, interest and
 * charges is expressed without anyone writing a formula. A screen that listed
 * these four fields separately would never let that be discovered.
 */
export interface SpineGroup {
  /** Null gathers everything that answers no line: dropped fields, fields with
   * no concept, and concepts left uncompared on purpose. */
  spineConceptId: string | null
  paths: string[]
  /** More than one field feeds this line, so the comparison is made on a sum. */
  summed: boolean
  /** Part of the sum is stated account by account and part as a total, so the
   * two halves cannot be added up into one comparable figure. */
  mixedComparison: boolean
}

/** The line a selection actually feeds, or null when it feeds none. */
function answeredSpine(selection: FieldSelectionInput): string | null {
  if (!selection.kept || !selection.conceptId) return null
  return selection.spineConceptId ?? null
}

/**
 * The field table arranged the way the comparison will read it.
 *
 * Groups keep the order in which their first field appears, so rearranging the
 * table never reorders under the reader; the unanswered group goes last because
 * it is the leftovers, not a line of the report.
 */
export function groupBySpineConcept(selections: readonly FieldSelectionInput[]): SpineGroup[] {
  const groups = new Map<string | null, FieldSelectionInput[]>()

  for (const selection of selections) {
    const key = answeredSpine(selection)
    const members = groups.get(key)
    if (members) members.push(selection)
    else groups.set(key, [selection])
  }

  const unanswered = groups.get(null)
  groups.delete(null)
  if (unanswered) groups.set(null, unanswered)

  return [...groups].map(([spineConceptId, members]) => ({
    spineConceptId,
    paths: members.map(member => member.path),
    summed: spineConceptId !== null && members.length > 1,
    mixedComparison:
      spineConceptId !== null
      && members.some(member => member.perAccount === true)
      && members.some(member => member.perAccount !== true)
  }))
}

/**
 * The fields claiming an account-by-account comparison without naming the
 * account.
 *
 * `toMappingDraft` downgrades these to a total rather than storing a comparison
 * that can only ever fail, and the screen has to say so: from the user's side
 * the difference is between a certificate that lists each account and one that
 * states a single figure, and only they can see which one they are holding.
 */
export function fieldsMissingAccountPath(
  selections: readonly FieldSelectionInput[]
): string[] {
  return selections
    .filter(
      selection =>
        selection.kept
        && selection.conceptId
        && selection.perAccount === true
        && !selection.accountPath
    )
    .map(selection => selection.path)
}
