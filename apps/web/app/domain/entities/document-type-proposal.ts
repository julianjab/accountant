/**
 * What the AI proposes after looking at one sample document.
 *
 * A proposal is stored nowhere: it is an offer the user trims before anything
 * is created, which is why it carries the document's own vocabulary (a label,
 * the value it read on the paper, the heading it sat under) alongside the
 * technical path. Without those the only thing left to choose by is a dotted
 * path, and nobody reading a certificate thinks in dotted paths.
 */

import type { ConceptMappingSign } from './concept-mapping'
import type { DocumentTypeField } from './document-type'

/** A proposed field is exactly a field description: the value read on the
 * sample used to live only here, and is now kept on the type itself, so the
 * editor can offer the same anchor the configurator does. Named separately
 * because a proposal is an offer and a description is stored. */
export type ProposedField = DocumentTypeField

/** A field the proposal already knows the meaning of. Narrower than a stored
 * mapping entry: the spine line and the per-account comparison are curation
 * the configuration screen adds later. */
export interface ProposedFieldMapping {
  fieldPath: string
  conceptId: string
  accountPath: string | null
  sign: ConceptMappingSign
}

/** A field the proposal deliberately left unmapped, and why. */
export interface UnmappedField {
  fieldPath: string
  reason: string
}

export interface DocumentTypeProposal {
  extractionPrompt: string
  extractionSchema: Record<string, unknown>
  fields: ProposedField[]
  fieldMappings: ProposedFieldMapping[]
  unmappedFields: UnmappedField[]
  /** The reconciliation model the proposal was made against, carried back on
   * creation so the mappings are stored against the same vocabulary. */
  kindId: string | null
  reporterPath: string | null
  reporterNamePath: string | null
  periodPath: string | null
}
