import type {
  ConceptMapping,
  ConceptMappingDraft,
  ConceptMappingEntry
} from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { ConceptMappingRepository } from '~/application/ports/concept-mapping-repository'

interface ConceptDto {
  id: string
  label: string
  role: string
  description: string
}

interface KindDto {
  id: string
  label: string
  period_granularity: string
  spine_concepts: ConceptDto[]
  evidence_concepts: ConceptDto[]
}

interface MappingEntryDto {
  field_path: string
  concept_id: string
  account_path: string | null
  sign: number
}

interface MappingDto {
  document_type_id: string
  kind_id: string
  entries: MappingEntryDto[]
  reporter_path: string | null
  reporter_name_path: string | null
  period_path: string | null
}

function toConcept(dto: ConceptDto): ReconciliationKind['evidenceConcepts'][number] {
  return { id: dto.id, label: dto.label, role: dto.role, description: dto.description }
}

function toKind(dto: KindDto): ReconciliationKind {
  return {
    id: dto.id,
    label: dto.label,
    periodGranularity: dto.period_granularity,
    spineConcepts: dto.spine_concepts.map(toConcept),
    evidenceConcepts: dto.evidence_concepts.map(toConcept)
  }
}

function toEntry(dto: MappingEntryDto): ConceptMappingEntry {
  return {
    fieldPath: dto.field_path,
    conceptId: dto.concept_id,
    accountPath: dto.account_path,
    // The server only ever stores +1 or -1; anything else would be a bug there
    // rather than a value the UI should invent a meaning for.
    sign: dto.sign === -1 ? -1 : 1
  }
}

function toMapping(dto: MappingDto): ConceptMapping {
  return {
    documentTypeId: dto.document_type_id,
    kindId: dto.kind_id,
    entries: dto.entries.map(toEntry),
    reporterPath: dto.reporter_path,
    reporterNamePath: dto.reporter_name_path,
    periodPath: dto.period_path
  }
}

function isNotFoundError(error: unknown): boolean {
  const candidate = error as { statusCode?: number, response?: { status?: number } }
  return (candidate?.statusCode ?? candidate?.response?.status) === 404
}

export class HttpConceptMappingRepository implements ConceptMappingRepository {
  constructor(private readonly baseUrl: string) {}

  private path(kindId: string, documentTypeId: string): string {
    return `/reconciliation/kinds/${kindId}/document-types/${documentTypeId}/mapping`
  }

  async listKinds(): Promise<ReconciliationKind[]> {
    const dtos = await $fetch<KindDto[]>('/reconciliation/kinds', {
      baseURL: this.baseUrl,
      credentials: 'include'
    })
    return dtos.map(toKind)
  }

  async get(kindId: string, documentTypeId: string): Promise<ConceptMapping | null> {
    try {
      const dto = await $fetch<MappingDto>(this.path(kindId, documentTypeId), {
        baseURL: this.baseUrl,
        credentials: 'include'
      })
      return toMapping(dto)
    } catch (error) {
      // A 404 means this type was never mapped, which the configuration screen
      // shows as an invitation rather than an error.
      if (isNotFoundError(error)) return null
      throw error
    }
  }

  async save(
    kindId: string,
    documentTypeId: string,
    draft: ConceptMappingDraft
  ): Promise<ConceptMapping> {
    const dto = await $fetch<MappingDto>(this.path(kindId, documentTypeId), {
      baseURL: this.baseUrl,
      method: 'PUT',
      credentials: 'include',
      body: {
        entries: draft.entries.map(entry => ({
          field_path: entry.fieldPath,
          concept_id: entry.conceptId,
          account_path: entry.accountPath,
          sign: entry.sign
        })),
        reporter_path: draft.reporterPath,
        reporter_name_path: draft.reporterNamePath,
        period_path: draft.periodPath
      }
    })
    return toMapping(dto)
  }
}
