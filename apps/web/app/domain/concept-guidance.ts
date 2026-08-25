/**
 * Answering, from what the model already declares, the questions the
 * configuration screen would otherwise ask twice.
 *
 * A document type's mapping asks two things of every figure: what it is, and
 * which line of the base report it answers. On a certificate that prints a
 * table those two are asked once per row — thirty-two choices from a list of
 * thirty on an employment certificate — and the second one is, for most
 * concepts, not a choice at all: the rule pack declares which claim a piece of
 * evidence backs, and for nineteen of twenty-four concepts it declares exactly
 * one.
 *
 * So the rules answer it, and the person is only asked where the model is
 * genuinely ambiguous. Nothing here guesses: every answer comes from a
 * correspondence somebody wrote down, and every one of them stays editable —
 * a derivation that turns out to be wired wrong has to be correctable without
 * a code change.
 */

import type { ReconciliationKind } from './entities/reconciliation-kind'

/** The claims this piece of evidence is declared to back. Empty when no rule
 * covers it, which is not the same as "it backs nothing in particular". */
export function spineAnsweredBy(
  kind: ReconciliationKind | null,
  conceptId: string | null
): string[] {
  if (!kind || !conceptId) return []
  return kind.answers[conceptId] ?? []
}

/**
 * The line to fill in on its own, or null when the person has to decide.
 *
 * Null covers both ways of not knowing, and they are different on screen: a
 * concept with several declared claims is a real question worth asking, while
 * one with none is a gap in the rule pack — the mapping will store fine and
 * reconcile against nothing.
 */
export function derivedSpineFor(
  kind: ReconciliationKind | null,
  conceptId: string | null
): string | null {
  const answered = spineAnsweredBy(kind, conceptId)
  return answered.length === 1 ? (answered[0] as string) : null
}

/** Whether the pair the mapping holds is one the rules actually compare.
 * A pair nobody declared stores happily and never reconciles, which is the
 * quietest way this screen can be wrong. */
export function isPairDeclared(
  kind: ReconciliationKind | null,
  conceptId: string | null,
  spineConceptId: string | null
): boolean {
  if (!conceptId || !spineConceptId) return true
  const answered = spineAnsweredBy(kind, conceptId)
  // No declared answer at all is reported by `spineAnsweredBy` being empty and
  // said in its own words on screen; it is not a mismatch.
  return answered.length === 0 || answered.includes(spineConceptId)
}

/**
 * The half of a concept id that says which kind of paper it belongs to.
 *
 * Concepts are namespaced by the document that certifies them — `payroll:` for
 * the employer's certificate, `bank:` for a bank's. A document is one of those
 * things, so once any figure on it has been named, the rest of the list is
 * mostly noise.
 */
export function conceptNamespace(conceptId: string): string {
  const cut = conceptId.indexOf(':')
  return cut < 0 ? '' : conceptId.slice(0, cut)
}

/**
 * The concept namespaces this document has already been said to speak.
 *
 * Derived from the answers given rather than declared anywhere: the first
 * figure someone names is chosen from everything, and from then on the screen
 * knows what kind of paper this is. Nothing to configure, and nothing lost —
 * the rest of the catalogue stays reachable, just further down.
 */
export function namespacesInUse(conceptIds: readonly (string | null)[]): Set<string> {
  const namespaces = new Set<string>()
  for (const conceptId of conceptIds) {
    if (conceptId) namespaces.add(conceptNamespace(conceptId))
  }
  return namespaces
}

/** One group of a dropdown: the likely answers, then everything else. */
export interface RankedConcepts<T> {
  likely: T[]
  rest: T[]
}

/**
 * The catalogue split into what this document plausibly says and the rest.
 *
 * Ordering rather than filtering, on purpose: a certificate that turns out to
 * certify two things — an employer that also reports an AFC deposit — must not
 * have the second one hidden from it because of what the first row said.
 */
export function rankConcepts<T extends { id: string }>(
  concepts: readonly T[],
  namespaces: ReadonlySet<string>
): RankedConcepts<T> {
  if (namespaces.size === 0) return { likely: [], rest: [...concepts] }
  return {
    likely: concepts.filter(concept => namespaces.has(conceptNamespace(concept.id))),
    rest: concepts.filter(concept => !namespaces.has(conceptNamespace(concept.id)))
  }
}

/** The same split for the base report's lines, ranked by what this concept is
 * declared to answer rather than by namespace — the lines all share one. */
export function rankSpineConcepts<T extends { id: string }>(
  concepts: readonly T[],
  answered: readonly string[]
): RankedConcepts<T> {
  if (answered.length === 0) return { likely: [], rest: [...concepts] }
  return {
    likely: concepts.filter(concept => answered.includes(concept.id)),
    rest: concepts.filter(concept => !answered.includes(concept.id))
  }
}
