import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { DocumentRepository } from '~/application/ports/document-repository'

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
}

interface ExtractedDataDto {
  id: string
  document_id: string
  fields: Record<string, unknown>
  confidence: number | null
  created_at: string
}

function toDocument(dto: DocumentDto): ClientDocument {
  return {
    id: dto.id,
    clientId: dto.client_id,
    documentTypeId: dto.document_type_id,
    driveFileId: dto.drive_file_id,
    fileName: dto.file_name,
    mimeType: dto.mime_type,
    status: dto.status,
    error: dto.error,
    createdAt: dto.created_at
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
    const dto = await $fetch<DocumentDto>(`/documents/${id}`, { baseURL: this.baseUrl })
    return toDocument(dto)
  }

  async getExtractedData(id: string): Promise<ExtractedData | null> {
    try {
      const dto = await $fetch<ExtractedDataDto>(`/documents/${id}/extracted-data`, {
        baseURL: this.baseUrl
      })
      return toExtractedData(dto)
    } catch (error) {
      if (isNotFoundError(error)) {
        return null
      }
      throw error
    }
  }
}
