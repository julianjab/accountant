import type { Client } from '~/domain/entities/client'
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ClientRepository } from '~/application/ports/client-repository'
import type { DocumentRepository } from '~/application/ports/document-repository'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

export interface ListInboxInput {
  status?: DocumentStatus
  now?: Date
}

export interface InboxTotals {
  unprocessed: number
  processedToday: number
  failed: number
  avgProcessingMs: number | null
}

export interface InboxGroup {
  client: Client
  documents: ClientDocument[]
}

export interface InboxView {
  totals: InboxTotals
  groups: InboxGroup[]
  totalDocuments: number
  filteredDocuments: number
  documentTypesById: Record<string, DocumentType>
}

const UNPROCESSED_STATUSES: DocumentStatus[] = ['pending', 'classifying', 'running_ocr']
// Approval only records a review decision (see the server's ApproveDocument) — it never
// reverses the OCR pipeline. A document stays "processed" for these figures whether or
// not it has since been approved (mirrors GetDocumentMetrics on the server).
const PROCESSED_STATUSES: DocumentStatus[] = ['processed', 'approved']

function matchesStatusFilter(documentStatus: DocumentStatus, filterStatus: DocumentStatus): boolean {
  // The "processed" filter must match every status counted in the processedToday/
  // avgProcessingMs totals above, or the metric card and the filtered list disagree.
  if (filterStatus === 'processed') return PROCESSED_STATUSES.includes(documentStatus)
  return documentStatus === filterStatus
}

function isSameLocalDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function computeTotals(documents: ClientDocument[], now: Date): InboxTotals {
  const unprocessed = documents.filter(d => UNPROCESSED_STATUSES.includes(d.status)).length
  const failed = documents.filter(d => d.status === 'failed').length

  const processedTodayDocs = documents.filter(
    d => PROCESSED_STATUSES.includes(d.status) && d.processedAt !== null && isSameLocalDay(new Date(d.processedAt), now)
  )

  const durationsMs = processedTodayDocs
    .filter((d): d is ClientDocument & { processedAt: string } => d.processedAt !== null)
    .map(d => new Date(d.processedAt).getTime() - new Date(d.createdAt).getTime())

  const avgProcessingMs = durationsMs.length > 0
    ? durationsMs.reduce((sum, ms) => sum + ms, 0) / durationsMs.length
    : null

  return {
    unprocessed,
    processedToday: processedTodayDocs.length,
    failed,
    avgProcessingMs
  }
}

export class ListInbox {
  constructor(
    private readonly documents: DocumentRepository,
    private readonly clients: ClientRepository,
    private readonly types: DocumentTypeRepository
  ) {}

  async execute(input?: ListInboxInput): Promise<InboxView> {
    const [documents, clients, types] = await Promise.all([
      this.documents.list(),
      this.clients.list(),
      this.types.list()
    ])
    const now = input?.now ?? new Date()

    const totals = computeTotals(documents, now)

    const filtered = input?.status
      ? documents.filter(d => matchesStatusFilter(d.status, input.status!))
      : documents

    const clientsById = new Map(clients.map(c => [c.id, c]))
    const documentsByClientId = new Map<string, ClientDocument[]>()
    for (const document of filtered) {
      const client = clientsById.get(document.clientId)
      if (!client) continue
      const bucket = documentsByClientId.get(document.clientId)
      if (bucket) {
        bucket.push(document)
      } else {
        documentsByClientId.set(document.clientId, [document])
      }
    }

    const groups: InboxGroup[] = [...documentsByClientId.entries()]
      .map(([clientId, docs]) => ({
        client: clientsById.get(clientId)!,
        documents: [...docs].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      }))
      .sort((a, b) => a.client.name.localeCompare(b.client.name) || a.client.id.localeCompare(b.client.id))

    const documentTypesById = Object.fromEntries(types.map(t => [t.id, t]))

    return {
      totals,
      groups,
      totalDocuments: documents.length,
      filteredDocuments: filtered.length,
      documentTypesById
    }
  }
}
