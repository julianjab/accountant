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
