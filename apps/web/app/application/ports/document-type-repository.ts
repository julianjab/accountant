import type {
  DocumentType,
  DocumentTypeCreation,
  DocumentTypeField,
  DocumentTypeUpdate
} from '~/domain/entities/document-type'
import type {
  DocumentTypeProposal,
  ProposedFieldMapping
} from '~/domain/entities/document-type-proposal'

/** Asking the AI what it makes of a sample document. Stores nothing: the
 * answer is an offer the user trims before a type exists. */
export interface ProposeDocumentTypeInput {
  name: string
  /**
   * A document already in a client's folder to read as the sample.
   *
   * Preferred over `sampleFile`: the type saves this id, so its field list
   * stays checkable against the paper it was derived from. An uploaded file
   * is gone once the request ends and leaves nothing to point back at.
   */
  documentId?: string | null
  sampleFile?: File | null
  /** The reconciliation model to propose concepts from; null lets the server
   * pick the one it knows. */
  kindId?: string | null
}

/**
 * Creating the type from what the user kept.
 *
 * No file and no AI call: the schema and the mappings are already trimmed to
 * the chosen fields, and the server stores exactly what it is sent.
 */
export interface CreateDocumentTypeInput {
  name: string
  description: string
  extractionPrompt: string
  extractionSchema: Record<string, unknown>
  fieldMappings: ProposedFieldMapping[]
  reporterPath: string | null
  reporterNamePath: string | null
  periodPath: string | null
  /** Empty means the type applies to any year. Non-empty is for an issuer that
   * changed its certificate between years. */
  taxYears: number[]
  /** The descriptions of the kept fields, taken from the proposal: what the
   * document calls each field and which block it sits in. */
  fields: DocumentTypeField[]
  kindId: string | null
  /** The document the proposal was made from, so the type remembers the paper
   * it came from. Null when the flow was not started from one. */
  sampleDocumentId: string | null
}

/** Every field is optional: the configuration screen sends only what it
 * changed, so two people editing different parts of a type do not overwrite
 * each other's work. */
export interface UpdateDocumentTypeInput {
  name?: string
  description?: string
  active?: boolean
  extractionPrompt?: string
  extractionSchema?: Record<string, unknown>
  /** Omitted keeps the stored descriptions; sent replaces them wholesale,
   * since an edit that trims the schema is exactly when they change. */
  fields?: DocumentTypeField[]
}

export interface DocumentTypeRepository {
  listActive: () => Promise<DocumentType[]>
  list: () => Promise<DocumentType[]>
  propose: (input: ProposeDocumentTypeInput) => Promise<DocumentTypeProposal>
  create: (input: CreateDocumentTypeInput) => Promise<DocumentTypeCreation>
  update: (id: string, changes: UpdateDocumentTypeInput) => Promise<DocumentTypeUpdate>
}
