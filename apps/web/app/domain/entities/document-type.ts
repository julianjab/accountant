import type { MappingChange } from '~/domain/entities/concept-mapping'
import type { UnmappedField } from '~/domain/entities/document-type-proposal'

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
  /**
   * What this field said on the sample the type was configured from; empty
   * when unknown, which is every type saved before it was carried.
   *
   * A path and a label still leave "which of these figures is it?" open on a
   * certificate that prints four of them — the configurator settles that by
   * showing the value, and the editor asks the same question of the same list.
   */
  sampleValue: string
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
  /** Empty means the type applies to any tax year. */
  taxYears: number[]
  /**
   * The document the configuration was derived from.
   *
   * Kept so whoever revisits the type can read the paper behind the choices:
   * a field list is only checkable against the document it came from.
   */
  sampleDocumentId: string | null
}

/**
 * The outcome of creating a type.
 *
 * Not `DocumentTypeUpdate`: creation and editing report different things.
 * An edit says how the stored mapping had to change to survive the new
 * schema; creation has no stored mapping to change, and instead says which
 * of the fields it was sent will be extracted but never reconciled — because
 * the AI declined to map them, or because the whole mapping was discarded for
 * want of a reporting party. Reading one as the other is how "the type saved
 * but its mapping did not" reaches the screen as clean success.
 */
export interface DocumentTypeCreation {
  documentType: DocumentType
  unmappedFields: UnmappedField[]
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
