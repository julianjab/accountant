import type { FieldSelection } from '~/domain/proposal-loop'
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
  /**
   * The type this proposal revises, when it is a regeneration.
   *
   * The server then starts from that type's stored prompt and schema and may
   * not rename what it already declares: the concept mappings are keyed by
   * path, so a regeneration that renamed a surviving field would throw away
   * every mapping someone curated to fix the one field that was missing.
   */
  documentTypeId?: string | null
  /**
   * What the person kept and threw out of the last reading.
   *
   * The answer to a proposal is the best instruction for the next one: without
   * it every round starts from the document alone and offers back the same
   * twenty fields that were just refused. Absent on a first reading, which has
   * no answer behind it yet.
   */
  selection?: FieldSelection | null
  /**
   * What the person configuring the type says the last reading got wrong.
   *
   * The lever the screen otherwise lacks: a table the model read as one row
   * stays one row however many times the same request is repeated, because
   * nothing in it ever said the other rows were missing.
   */
  guidance?: string | null
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
  /** What the type declares about itself, for the papers that never say it.
   * Without these the server discards every mapping of a type whose documents
   * do not print their own issuer — the case they exist for. */
  reporterTaxId: string | null
  reporterName: string | null
  period: string | null
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
  /** The document the configuration comes from. Settable after the fact so a
   * type configured before samples were recorded stops being uncheckable. */
  sampleDocumentId?: string
}

/**
 * Asking the AI what a document calls the fields a type already declares.
 *
 * Not a proposal: a fresh proposal invents its own field names and lines up
 * with the stored schema only by chance, so a re-reading meant to fill in
 * missing labels routinely recovered nothing at all. Here the type's own paths
 * are the question, and the answer can only describe them.
 */
export interface DescribeDocumentTypeFieldsInput {
  /** The paper to read. A stored document, because the descriptions are only
   * worth keeping when the type can point back at what they came from. */
  documentId: string
}

export interface DocumentTypeRepository {
  listActive: () => Promise<DocumentType[]>
  list: () => Promise<DocumentType[]>
  propose: (input: ProposeDocumentTypeInput) => Promise<DocumentTypeProposal>
  /** Stores nothing: the caller decides how these meet the descriptions it
   * already curated. */
  describeFields: (
    id: string,
    input: DescribeDocumentTypeFieldsInput
  ) => Promise<DocumentTypeField[]>
  create: (input: CreateDocumentTypeInput) => Promise<DocumentTypeCreation>
  update: (id: string, changes: UpdateDocumentTypeInput) => Promise<DocumentTypeUpdate>
  /** Throws DocumentTypeInUseError when documents were classified as it. */
  remove: (id: string) => Promise<void>
}
