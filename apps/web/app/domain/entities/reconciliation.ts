/**
 * A reconciliation report as the web reads it.
 *
 * Amounts stay strings all the way through. They are exact decimals on the
 * server and JavaScript numbers are doubles, so parsing them would risk
 * showing a discrepancy the engine never found — the one thing this screen
 * must never do.
 */

export type FindingStatus
  = | 'matched'
    | 'matched_within_tolerance'
    | 'mismatch'
    | 'missing_evidence'
    | 'unsupported_by_spine'
    | 'out_of_scope'

export interface ReconciliationFact {
  sourceId: string
  role: 'spine' | 'evidence'
  reporterTaxId: string
  reporterName: string
  conceptId: string
  amount: string
  account: string | null
  detail: string
  /** Where inside the source this sits — `row 37`, a file name — so a reader
   * can go back to the document the figure came from. */
  locator: string
}

export interface ReconciliationFinding {
  id: string
  status: FindingStatus
  ruleId: string | null
  label: string
  reporterTaxId: string
  reporterName: string
  spineAmount: string
  evidenceAmount: string
  delta: string
  account: string | null
  accountMatch: string
  note: string
  spineFacts: ReconciliationFact[]
  evidenceFacts: ReconciliationFact[]
}

/** What a document ended up doing for the reconciliation.
 *
 * Only `contributed` and `spine_parsed` mean the figures arrived; every other
 * value is a reason some amount that should be reconciling is not. */
export type ContributionStatus
  = | 'contributed'
    | 'spine_parsed'
    | 'not_ready'
    | 'not_classified'
    | 'type_not_mapped'
    | 'no_extraction'
    | 'no_reporting_party'
    | 'other_period'
    | 'no_amounts'
    | 'unreadable'

export interface ReconciliationContribution {
  documentId: string
  fileName: string
  status: ContributionStatus
  factCount: number
  /** Whatever makes the status actionable — the field that could not name the
   * reporting party, the year the certificate turned out to cover, the intake
   * error. Empty when the status speaks for itself. */
  detail: string
}

export interface ReconciliationSummary {
  counts: Record<string, number>
  totalFindings: number
  reconciled: number
  needingAttention: number
}

export interface ReconciliationReport {
  id: string
  clientId: string
  kindId: string
  period: string
  generatedAt: string
  summary: ReconciliationSummary
  findings: ReconciliationFinding[]
  /** One entry per document the run looked at, whether or not it helped. */
  contributions: ReconciliationContribution[]
}

/** The two outcomes that mean the document did its job. Anything else is a
 * figure missing from the reconciliation, however innocuous the wording. */
export function isContributing(status: ContributionStatus): boolean {
  return status === 'contributed' || status === 'spine_parsed'
}

/** Attention first, then what already reconciles, then what was not checked. */
export const FINDING_ORDER: FindingStatus[] = [
  'mismatch',
  'missing_evidence',
  'unsupported_by_spine',
  'matched_within_tolerance',
  'matched',
  'out_of_scope'
]
