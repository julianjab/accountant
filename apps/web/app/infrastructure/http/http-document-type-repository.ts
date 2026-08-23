import type { DocumentType } from '~/domain/entities/document-type'
import type { DefineDocumentTypeInput, DocumentTypeRepository } from '~/application/ports/document-type-repository'

interface DocumentTypeDto {
  id: string
  name: string
  description: string
  extraction_prompt: string
  extraction_schema: Record<string, unknown>
  active: boolean
  created_at: string
}

function toDocumentType(dto: DocumentTypeDto): DocumentType {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description,
    extractionPrompt: dto.extraction_prompt,
    extractionSchema: dto.extraction_schema,
    active: dto.active,
    createdAt: dto.created_at
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

  async list(): Promise<DocumentType[]> {
    const dtos = await $fetch<DocumentTypeDto[]>('/document-types', {
      baseURL: this.baseUrl,
      credentials: 'include'
    })
    return dtos.map(toDocumentType)
  }

  async define(input: DefineDocumentTypeInput): Promise<DocumentType> {
    const formData = new FormData()
    formData.append('name', input.name)
    formData.append('description', input.description)
    formData.append('sample_file', input.sampleFile)

    const dto = await $fetch<DocumentTypeDto>('/document-types', {
      baseURL: this.baseUrl,
      method: 'POST',
      credentials: 'include',
      body: formData
    })
    return toDocumentType(dto)
  }
}
