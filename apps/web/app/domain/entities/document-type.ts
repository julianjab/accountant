import type { MappingChange } from '~/domain/entities/concept-mapping'
import type { DocumentTypeField } from '~/domain/field-sections'

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
   * came from. Empty for types configured before descriptions existed, which
   * every screen reading this must still render.
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
