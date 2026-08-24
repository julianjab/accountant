import type { MappingChange } from '~/domain/entities/concept-mapping'

export interface DocumentType {
  id: string
  name: string
  description: string
  extractionPrompt: string
  extractionSchema: Record<string, unknown>
  active: boolean
  createdAt: string
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
