/**
 * The vocabulary a reconciliation model publishes.
 *
 * The document type configuration screen offers `evidenceConcepts` as the
 * closed list an extracted field may be mapped onto: the server rejects any
 * other id, so the UI must never let one be typed by hand.
 */

export interface ReconciliationConcept {
  id: string
  label: string
  role: string
  description: string
}

export interface ReconciliationKind {
  id: string
  label: string
  periodGranularity: string
  spineConcepts: ReconciliationConcept[]
  evidenceConcepts: ReconciliationConcept[]
}
