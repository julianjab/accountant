import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type {
  ClientDocumentsImport,
  DocumentListFilter,
  DocumentRepository
} from '~/application/ports/document-repository'

interface DocumentDto {
  id: string
  client_id: string
  document_type_id: string | null
  drive_file_id: string
  file_name: string
  mime_type: string
  status: DocumentStatus
  error: string | null
  created_at: string
  processed_at: string | null
  source_id: string | null
}

interface ExtractedDataDto {
  id: string
  document_id: string
  fields: Record<string, unknown>
  confidence: number | null
  created_at: string
}

function toClientDocument(dto: DocumentDto): ClientDocument {
  return {
    id: dto.id,
    clientId: dto.client_id,
    documentTypeId: dto.document_type_id,
    driveFileId: dto.drive_file_id,
    fileName: dto.file_name,
    mimeType: dto.mime_type,
    status: dto.status,
    error: dto.error,
    createdAt: dto.created_at,
    processedAt: dto.processed_at,
    sourceId: dto.source_id ?? null
  }
}

function toExtractedData(dto: ExtractedDataDto): ExtractedData {
  return {
    id: dto.id,
    documentId: dto.document_id,
    fields: dto.fields,
    confidence: dto.confidence,
    createdAt: dto.created_at
  }
}

function isNotFoundError(error: unknown): boolean {
  const status = (error as { statusCode?: number, response?: { status?: number } })?.statusCode
    ?? (error as { statusCode?: number, response?: { status?: number } })?.response?.status
  return status === 404
}

export class HttpDocumentRepository implements DocumentRepository {
  constructor(private readonly baseUrl: string) {}

  async getById(id: string): Promise<ClientDocument> {
    const dto = await $fetch<DocumentDto>(`/documents/${id}`, {
      baseURL: this.baseUrl,
      credentials: 'include'
    })
    return toClientDocument(dto)
  }

  async getExtractedData(id: string): Promise<ExtractedData | null> {
    try {
      const dto = await $fetch<ExtractedDataDto>(`/documents/${id}/extracted-data`, {
        baseURL: this.baseUrl,
        credentials: 'include'
      })
      return toExtractedData(dto)
    } catch (error) {
      if (isNotFoundError(error)) {
        return null
      }
      throw error
    }
  }

  async listByClient(clientId: string): Promise<ClientDocument[]> {
    const dtos = await $fetch<DocumentDto[]>(`/clients/${clientId}/documents`, {
      baseURL: this.baseUrl,
      credentials: 'include'
    })
    return dtos.map(toClientDocument)
  }

  async importForClient(clientId: string): Promise<ClientDocumentsImport> {
    const dto = await $fetch<{
      imported: DocumentDto[]
      failed: DocumentDto[]
      unreadable: string[]
      skipped: number
    }>(`/clients/${clientId}/documents/import`, {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST'
    })
    return {
      imported: dto.imported.map(toClientDocument),
      failed: dto.failed.map(toClientDocument),
      unreadable: dto.unreadable,
      skipped: dto.skipped
    }
  }

  async reprocess(id: string): Promise<ClientDocument> {
    const dto = await $fetch<DocumentDto>(`/documents/${id}/reprocess`, {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST'
    })
    return toClientDocument(dto)
  }

  async approve(id: string, approvedBy?: string): Promise<ClientDocument> {
    const dto = await $fetch<DocumentDto>(`/documents/${id}/approve`, {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST',
      body: { approved_by: approvedBy ?? null }
    })
    return toClientDocument(dto)
  }

  async list(filter?: DocumentListFilter): Promise<ClientDocument[]> {
    const dtos = await $fetch<DocumentDto[]>('/documents', {
      baseURL: this.baseUrl,
      credentials: 'include',
      params: { status: filter?.status }
    })
    return dtos.map(toClientDocument)
  }
}
