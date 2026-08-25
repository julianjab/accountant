import { isEmptySelection } from '~/domain/proposal-loop'
import type {
  DocumentType,
  DocumentTypeCreation,
  DocumentTypeField,
  DocumentTypeUpdate,
  FieldRole
} from '~/domain/entities/document-type'
import type { ConceptMappingSign, MappingChange } from '~/domain/entities/concept-mapping'
import { DocumentTypeInUseError } from '~/domain/errors/document-type-in-use-error'
import type {
  DocumentTypeProposal,
  ProposedField,
  ProposedFieldMapping,
  UnmappedField
} from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  DescribeDocumentTypeFieldsInput,
  DocumentTypeRepository,
  ProposeDocumentTypeInput,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'

interface DocumentTypeFieldDto {
  path: string
  label?: string | null
  role?: string | null
  section?: string | null
  sample_value?: string | null
}

interface DocumentTypeDto {
  id: string
  name: string
  description: string
  extraction_prompt: string
  extraction_schema: Record<string, unknown>
  candidate_schema?: Record<string, unknown> | null
  active: boolean
  created_at: string
  fields?: DocumentTypeFieldDto[]
  tax_years?: number[]
  sample_document_id?: string | null
}

interface MappingChangeDto {
  kind_id: string
  change: string
  path: string | null
  field_path: string | null
  concept_id: string | null
  reason: string
}

/** What POST /document-types answers: the type, plus the fields it will
 * extract but cannot reconcile. It carries no `mapping_changes`. */
interface CreatedDocumentTypeDto extends DocumentTypeDto {
  kind_id?: string | null
  unmapped_fields?: UnmappedFieldDto[]
}

interface UpdatedDocumentTypeDto extends DocumentTypeDto {
  mapping_changes?: MappingChangeDto[]
}

interface ProposedFieldDto {
  path: string
  label?: string | null
  role?: string | null
  sample_value?: string | null
  section?: string | null
}

interface ProposedFieldMappingDto {
  field_path: string
  concept_id: string
  account_path?: string | null
  sign?: number | null
}

interface UnmappedFieldDto {
  field_path: string
  reason?: string | null
}

interface DocumentTypeProposalDto {
  extraction_prompt: string
  extraction_schema: Record<string, unknown>
  fields?: ProposedFieldDto[]
  field_mappings?: ProposedFieldMappingDto[]
  unmapped_fields?: UnmappedFieldDto[]
  kind_id?: string | null
  reporter_path?: string | null
  reporter_name_path?: string | null
  period_path?: string | null
}

const ROLES: FieldRole[] = ['identifier', 'amount', 'context']

/** An unknown role is read as context: it only decides whether the field
 * starts selected, and starting a field the app cannot interpret as selected
 * would push it into the type without the user having chosen it. */
function toRole(value: string | null | undefined): FieldRole {
  return ROLES.includes(value as FieldRole) ? (value as FieldRole) : 'context'
}

function toDocumentTypeField(dto: DocumentTypeFieldDto): DocumentTypeField {
  return {
    path: dto.path,
    // The path is the only label a type saved before descriptions existed can
    // offer, and a blank line in a list is worse than a technical one.
    label: dto.label || dto.path,
    role: toRole(dto.role),
    section: dto.section ?? '',
    sampleValue: dto.sample_value ?? ''
  }
}

function toFieldDto(field: DocumentTypeField): DocumentTypeFieldDto {
  return {
    path: field.path,
    label: field.label,
    role: field.role,
    section: field.section,
    sample_value: field.sampleValue
  }
}

function toSign(value: number | null | undefined): ConceptMappingSign {
  return value === -1 ? -1 : 1
}

function toProposedField(dto: ProposedFieldDto): ProposedField {
  return {
    path: dto.path,
    label: dto.label ?? '',
    role: toRole(dto.role),
    sampleValue: dto.sample_value ?? '',
    section: dto.section ?? ''
  }
}

function toProposedFieldMapping(dto: ProposedFieldMappingDto): ProposedFieldMapping {
  return {
    fieldPath: dto.field_path,
    conceptId: dto.concept_id,
    accountPath: dto.account_path ?? null,
    sign: toSign(dto.sign)
  }
}

function toUnmappedField(dto: UnmappedFieldDto): UnmappedField {
  return { fieldPath: dto.field_path, reason: dto.reason ?? '' }
}

function toProposal(dto: DocumentTypeProposalDto): DocumentTypeProposal {
  return {
    extractionPrompt: dto.extraction_prompt,
    extractionSchema: dto.extraction_schema,
    fields: (dto.fields ?? []).map(toProposedField),
    fieldMappings: (dto.field_mappings ?? []).map(toProposedFieldMapping),
    unmappedFields: (dto.unmapped_fields ?? []).map(toUnmappedField),
    kindId: dto.kind_id ?? null,
    reporterPath: dto.reporter_path ?? null,
    reporterNamePath: dto.reporter_name_path ?? null,
    periodPath: dto.period_path ?? null
  }
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
    candidateSchema: dto.candidate_schema ?? null,
    active: dto.active,
    createdAt: dto.created_at,
    fields: (dto.fields ?? []).map(toDocumentTypeField),
    taxYears: dto.tax_years ?? [],
    sampleDocumentId: dto.sample_document_id ?? null
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

  async propose(input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    const formData = new FormData()
    formData.append('name', input.name)
    // Multipart either way: the endpoint takes one form, and naming a stored
    // document is just the other way of saying which sample to read.
    if (input.documentId) formData.append('document_id', input.documentId)
    else if (input.sampleFile) formData.append('sample_file', input.sampleFile)
    if (input.kindId) formData.append('kind_id', input.kindId)
    if (input.documentTypeId) formData.append('document_type_id', input.documentTypeId)
    if (input.guidance) formData.append('guidance', input.guidance)
    // JSON in a form field: multipart cannot nest, and a kept field is three
    // values (its path, the name the person gave it, a note aimed at it).
    if (input.selection && !isEmptySelection(input.selection)) {
      formData.append('selection', JSON.stringify(input.selection))
    }

    const dto = await $fetch<DocumentTypeProposalDto>('/document-types/proposals', {
      baseURL: this.baseUrl,
      method: 'POST',
      credentials: 'include',
      body: formData
    })
    return toProposal(dto)
  }

  async describeFields(
    id: string,
    input: DescribeDocumentTypeFieldsInput
  ): Promise<DocumentTypeField[]> {
    // Multipart like the proposal endpoint, which takes the sample the same
    // two ways; only a stored document is offered here.
    const formData = new FormData()
    formData.append('document_id', input.documentId)

    const dto = await $fetch<{ fields?: DocumentTypeFieldDto[] }>(
      `/document-types/${id}/field-descriptions`,
      {
        baseURL: this.baseUrl,
        method: 'POST',
        credentials: 'include',
        body: formData
      }
    )
    return (dto.fields ?? []).map(toDocumentTypeField)
  }

  async create(input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    const dto = await $fetch<CreatedDocumentTypeDto>('/document-types', {
      baseURL: this.baseUrl,
      method: 'POST',
      credentials: 'include',
      body: {
        name: input.name,
        description: input.description,
        extraction_prompt: input.extractionPrompt,
        extraction_schema: input.extractionSchema,
        candidate_schema: input.candidateSchema ?? null,
        field_mappings: input.fieldMappings.map(mapping => ({
          field_path: mapping.fieldPath,
          concept_id: mapping.conceptId,
          account_path: mapping.accountPath,
          sign: mapping.sign
        })),
        reporter_path: input.reporterPath,
        reporter_tax_id: input.reporterTaxId,
        reporter_name: input.reporterName,
        period: input.period,
        reporter_name_path: input.reporterNamePath,
        period_path: input.periodPath,
        tax_years: input.taxYears,
        fields: input.fields.map(toFieldDto),
        kind_id: input.kindId,
        sample_document_id: input.sampleDocumentId
      }
    })
    return {
      documentType: toDocumentType(dto),
      // Creation reports `unmapped_fields`, not `mapping_changes` — there is no
      // stored mapping yet to have changed. This is where the server says a
      // field it was sent will be extracted but never reconciled, including
      // the case where it discarded every mapping for want of a reporting
      // party, so reading the wrong key here shows that as a clean success.
      unmappedFields: (dto.unmapped_fields ?? []).map(toUnmappedField)
    }
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
    // Omitted keeps the stored one: an edit that only trims what is extracted
    // must not throw away what was on offer.
    if (changes.candidateSchema !== undefined) body.candidate_schema = changes.candidateSchema
    if (changes.fields !== undefined) body.fields = changes.fields.map(toFieldDto)
    if (changes.sampleDocumentId !== undefined) body.sample_document_id = changes.sampleDocumentId

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

  async remove(id: string): Promise<void> {
    try {
      await $fetch(`/document-types/${id}`, {
        baseURL: this.baseUrl,
        method: 'DELETE',
        credentials: 'include'
      })
    } catch (error) {
      // 409 is the server refusing because documents are filed under the type,
      // which is not a failure to retry but a different thing to offer.
      const status = (error as { statusCode?: number, status?: number })?.statusCode
        ?? (error as { status?: number })?.status
      if (status === 409) {
        const detail = (error as { data?: { detail?: string } })?.data?.detail ?? ''
        throw new DocumentTypeInUseError(detail)
      }
      throw error
    }
  }
}
