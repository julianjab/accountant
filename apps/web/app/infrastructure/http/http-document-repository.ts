import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
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
    createdAt: dto.created_at
  }
}

export class HttpDocumentRepository implements DocumentRepository {
  constructor(private readonly baseUrl: string) {}

  async listByClient(clientId: string): Promise<ClientDocument[]> {
    const dtos = await $fetch<DocumentDto[]>(`/clients/${clientId}/documents`, {
      baseURL: this.baseUrl
    })
    return dtos.map(toClientDocument)
  }
}
