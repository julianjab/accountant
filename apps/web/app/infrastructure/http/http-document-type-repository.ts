import type { DocumentType, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type { MappingChange } from '~/domain/entities/concept-mapping'
import type {
  DefineDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'

interface DocumentTypeDto {
  id: string
  name: string
  description: string
  extraction_prompt: string
  extraction_schema: Record<string, unknown>
  active: boolean
  created_at: string
}

interface MappingChangeDto {
  kind_id: string
  change: string
  path: string | null
  field_path: string | null
  concept_id: string | null
  reason: string
}

interface UpdatedDocumentTypeDto extends DocumentTypeDto {
  mapping_changes?: MappingChangeDto[]
}

function toMappingChange(dto: MappingChangeDto): MappingChange {
  return {
    kindId: dto.kind_id,
    change: dto.change,
    path: dto.path,
    fieldPath: dto.field_path,
    conceptId: dto.concept_id,
    reason: dto.reason
  }
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
      credentials: 'include',
      query: { active_only: false }
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

  async update(id: string, changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    // Only the keys the caller set are sent: PATCH leaves the rest alone, and
    // resending an unchanged extraction_schema would make the server re-check
    // the mapping against it for nothing.
    const body: Record<string, unknown> = {}
    if (changes.name !== undefined) body.name = changes.name
    if (changes.description !== undefined) body.description = changes.description
    if (changes.active !== undefined) body.active = changes.active
    if (changes.extractionPrompt !== undefined) body.extraction_prompt = changes.extractionPrompt
    if (changes.extractionSchema !== undefined) body.extraction_schema = changes.extractionSchema

    const dto = await $fetch<UpdatedDocumentTypeDto>(`/document-types/${id}`, {
      baseURL: this.baseUrl,
      method: 'PATCH',
      credentials: 'include',
      body
    })
    return {
      documentType: toDocumentType(dto),
      mappingChanges: (dto.mapping_changes ?? []).map(toMappingChange)
    }
  }
}
