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
