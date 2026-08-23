import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

interface DocumentTypeDto {
  id: string
  name: string
  active: boolean
}

function toDocumentType(dto: DocumentTypeDto): DocumentType {
  return {
    id: dto.id,
    name: dto.name,
    active: dto.active
  }
}

export class HttpDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly baseUrl: string) {}

  async listActive(): Promise<DocumentType[]> {
    const dtos = await $fetch<DocumentTypeDto[]>('/document-types', {
      baseURL: this.baseUrl,
      credentials: 'include',
      query: { active_only: true }
    })
    return dtos.map(toDocumentType)
  }
}
