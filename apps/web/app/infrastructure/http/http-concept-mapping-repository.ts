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
  spine_concept_id?: string | null
  per_account?: boolean
  row_label_path?: string | null
  row_label?: string | null
}

interface MappingDto {
  document_type_id: string
  kind_id: string
  entries: MappingEntryDto[]
  reporter_path: string | null
  reporter_name_path: string | null
  period_path: string | null
  reporter_tax_id?: string | null
  reporter_name?: string | null
  period?: string | null
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
    sign: dto.sign === -1 ? -1 : 1,
    // A mapping stored before the server knew about these reads as "extracted
    // but compared against nothing", which is what it did back then.
    spineConceptId: dto.spine_concept_id ?? null,
    perAccount: dto.per_account === true,
    // Both or neither. Half the pair would widen the entry to claim every row
    // of its table, which is the misreading the pair exists to prevent — and a
    // mapping stored before the server knew about tables has neither.
    rowLabelPath: dto.row_label && dto.row_label_path ? dto.row_label_path : null,
    rowLabel: dto.row_label && dto.row_label_path ? dto.row_label : null
  }
}

function toMapping(dto: MappingDto): ConceptMapping {
  return {
    documentTypeId: dto.document_type_id,
    kindId: dto.kind_id,
    entries: dto.entries.map(toEntry),
    reporterPath: dto.reporter_path,
    reporterNamePath: dto.reporter_name_path,
    periodPath: dto.period_path,
    reporterTaxId: dto.reporter_tax_id ?? null,
    reporterName: dto.reporter_name ?? null,
    period: dto.period ?? null
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
          sign: entry.sign,
          spine_concept_id: entry.spineConceptId,
          per_account: entry.perAccount,
          row_label_path: entry.rowLabelPath,
          row_label: entry.rowLabel
        })),
        reporter_path: draft.reporterPath,
        reporter_name_path: draft.reporterNamePath,
        period_path: draft.periodPath,
        reporter_tax_id: draft.reporterTaxId,
        reporter_name: draft.reporterName,
        period: draft.period
      }
    })
    return toMapping(dto)
  }
}
