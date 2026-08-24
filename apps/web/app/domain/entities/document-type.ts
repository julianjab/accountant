import type { MappingChange } from '~/domain/entities/concept-mapping'

/**
 * What a field is for.
 *
 * It is what a screen sorts by and what the create flow selects by: an
 * accountant keeps the identification and the amounts, and the rest is the
 * wording around them.
 */
export type FieldRole = 'identifier' | 'amount' | 'context'

/**
 * One extracted field, described the way the document describes it.
 *
 * Stored on the type rather than derived per screen: the schema knows a path
 * and a JSON type, neither of which says what the paper calls the field or
 * which block of the page it sits in.
 */
export interface DocumentTypeField {
  path: string
  label: string
  role: FieldRole
  /** The block of the document this field belongs to; empty when unknown. */
  section: string
}

export interface DocumentType {
  id: string
  name: string
  description: string
  extractionPrompt: string
  extractionSchema: Record<string, unknown>
  active: boolean
  createdAt: string
  /**
   * What each extracted field is called and which block of the document it
   * came from. Empty for a type saved before descriptions existed, or one
   * created from a proposal that described nothing — every screen reading
   * this must still render with only paths to work from.
   */
  fields: DocumentTypeField[]
}

/**
 * The outcome of editing a type, mapping consequences included.
 *
 * Trimming a field the concept mapping referred to forces the server to drop
 * that part of the mapping. The caller gets told which, because a curated
 * mapping disappearing in silence is exactly the failure this editor exists to
 * prevent.
 */
export interface DocumentTypeUpdate {
  documentType: DocumentType
  mappingChanges: MappingChange[]
}
