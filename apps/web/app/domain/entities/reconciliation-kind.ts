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
  /**
   * For each evidence concept, the claims the model's rules declare it backs.
   *
   * A rule is an assertion that its two sides mean the same thing, so this
   * already answers "which line of the base report does this figure belong
   * to" — with exactly one line for most concepts. It is what lets the
   * configuration screen stop asking a question that is already written down.
   *
   * A concept missing from here is backed by no rule: nothing to offer, and
   * the screen has to say so instead of guessing.
   */
  answers: Record<string, string[]>
}
