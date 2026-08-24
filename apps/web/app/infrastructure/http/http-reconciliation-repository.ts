import type {
  FindingStatus,
  ReconciliationFact,
  ReconciliationFinding,
  ReconciliationReport
} from '~/domain/entities/reconciliation'
import type { ReconciliationRepository } from '~/application/ports/reconciliation-repository'

interface FactDto {
  source_id: string
  role: 'spine' | 'evidence'
  reporter_tax_id: string
  reporter_name: string
  concept_id: string
  amount: string
  account: string | null
  detail: string
  locator: string
}

interface FindingDto {
  id: string
  status: FindingStatus
  rule_id: string | null
  label: string
  reporter_tax_id: string
  reporter_name: string
  spine_amount: string
  evidence_amount: string
  delta: string
  account: string | null
  account_match: string
  note: string
  spine_facts: FactDto[]
  evidence_facts: FactDto[]
}

interface ReportDto {
  id: string
  client_id: string
  kind_id: string
  period: string
  generated_at: string
  summary: {
    counts: Record<string, number>
    total_findings: number
    reconciled: number
    needing_attention: number
  }
  findings: FindingDto[]
}

function toFact(dto: FactDto): ReconciliationFact {
  return {
    sourceId: dto.source_id,
    role: dto.role,
    reporterTaxId: dto.reporter_tax_id,
    reporterName: dto.reporter_name,
    conceptId: dto.concept_id,
    amount: dto.amount,
    account: dto.account,
    detail: dto.detail,
    locator: dto.locator
  }
}

function toFinding(dto: FindingDto): ReconciliationFinding {
  return {
    id: dto.id,
    status: dto.status,
    ruleId: dto.rule_id,
    label: dto.label,
    reporterTaxId: dto.reporter_tax_id,
    reporterName: dto.reporter_name,
    spineAmount: dto.spine_amount,
    evidenceAmount: dto.evidence_amount,
    delta: dto.delta,
    account: dto.account,
    accountMatch: dto.account_match,
    note: dto.note,
    spineFacts: dto.spine_facts.map(toFact),
    evidenceFacts: dto.evidence_facts.map(toFact)
  }
}

function toReport(dto: ReportDto): ReconciliationReport {
  return {
    id: dto.id,
    clientId: dto.client_id,
    kindId: dto.kind_id,
    period: dto.period,
    generatedAt: dto.generated_at,
    summary: {
      counts: dto.summary.counts,
      totalFindings: dto.summary.total_findings,
      reconciled: dto.summary.reconciled,
      needingAttention: dto.summary.needing_attention
    },
    findings: dto.findings.map(toFinding)
  }
}

function isNotFoundError(error: unknown): boolean {
  const status = (error as { statusCode?: number, response?: { status?: number } })?.statusCode
    ?? (error as { statusCode?: number, response?: { status?: number } })?.response?.status
  return status === 404
}

export class HttpReconciliationRepository implements ReconciliationRepository {
  constructor(private readonly baseUrl: string) {}

  private path(kindId: string, clientId: string, period: string): string {
    return `/reconciliation/kinds/${kindId}/clients/${clientId}/periods/${period}`
  }

  async getReport(
    kindId: string,
    clientId: string,
    period: string
  ): Promise<ReconciliationReport | null> {
    try {
      const dto = await $fetch<ReportDto>(this.path(kindId, clientId, period), {
        baseURL: this.baseUrl,
        credentials: 'include'
      })
      return toReport(dto)
    } catch (error) {
      // A 404 here means no reconciliation has been run yet, which the screen
      // shows as an invitation rather than an error.
      if (isNotFoundError(error)) return null
      throw error
    }
  }

  async run(kindId: string, clientId: string, period: string): Promise<ReconciliationReport> {
    const dto = await $fetch<ReportDto>(this.path(kindId, clientId, period), {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST'
    })
    return toReport(dto)
  }
}
