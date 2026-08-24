/**
 * How a document type's extracted fields project onto a kind's concepts.
 *
 * `reporterPath` is load-bearing: a fact that cannot be attributed to a
 * reporting party is discarded by the projection, so a mapping without it
 * yields nothing at all no matter how many entries it carries.
 */

/** The document states the figure with the opposite sign to the concept. */
export type ConceptMappingSign = 1 | -1

export interface ConceptMappingEntry {
  /** Dotted path into the extracted fields; a `[]` segment walks a list. */
  fieldPath: string
  conceptId: string
  accountPath: string | null
  sign: ConceptMappingSign
  /**
   * The spine concept — the line of the base report — this field answers.
   *
   * Null means the field is extracted and projected into a fact, but nothing
   * is compared against it. Several entries may name the same spine concept:
   * the engine adds their amounts up before comparing, which is how a debt the
   * base report states once and the certificate splits into capital, interest
   * and charges is expressed without a formula.
   */
  spineConceptId: string | null
  /**
   * Whether the comparison is made account by account instead of on the
   * reporting party's total.
   *
   * Only truthful when both sides name the account: a certificate that states
   * a consolidated figure has no account to pair against, so asking for one
   * turns a figure it does certify into a missing one.
   */
  perAccount: boolean
}

export interface ConceptMappingDraft {
  entries: ConceptMappingEntry[]
  reporterPath: string | null
  reporterNamePath: string | null
  periodPath: string | null
}

export interface ConceptMapping extends ConceptMappingDraft {
  documentTypeId: string
  kindId: string
}

/**
 * Whether a stored mapping still says anything.
 *
 * The server has no delete, so clearing a mapping — which it does on its own
 * when a schema edit removes the field that held the reporting party — stores
 * an empty one instead. That is the same situation as never having mapped the
 * type, and showing it as a configured mapping would hide that the type stopped
 * reconciling.
 */
export function isConceptMappingCleared(mapping: ConceptMapping): boolean {
  return mapping.entries.length === 0 && !mapping.reporterPath
}

/** What the server had to change about a mapping to keep it consistent with a
 * schema edit. */
export type MappingChangeKind
  = | 'entry_dropped'
    | 'path_cleared'
    | 'mapping_cleared'
    | 'prune_failed'

export interface MappingChange {
  kindId: string
  change: MappingChangeKind | string
  path: string | null
  fieldPath: string | null
  conceptId: string | null
  reason: string
}
