/**
 * Reading a document type is a conversation, not a verdict.
 *
 * The first proposal is an offer: twenty fields where the accountant wants an
 * identifier and three figures, a table collapsed into a single row, a label
 * that is not what anyone in the office calls that figure. Every one of those
 * is answered by *choosing*, and the choice is a better instruction for the
 * next reading than any description of the document could be — so it goes back
 * to the model instead of being spent on a one-way apply.
 *
 * These are the rules of that loop: what the answer looks like on the wire,
 * and how a round's choices survive into the next round's rows.
 */

import type { ProposalFieldRow } from './document-type-configuration'
import { rowLabel } from './document-type-configuration'

/** One field the person kept, in their words. */
export interface KeptField {
  path: string
  label: string
  note: string
}

/** The answer to a proposal, as the server takes it. */
export interface FieldSelection {
  kept: KeptField[]
  /** Paths that were offered, read, and refused — which the model is told not
   * to propose again. Distinct from a path nobody ever mentioned. */
  dropped: string[]
}

/**
 * The rows as an answer the next reading can be steered by.
 *
 * Every unticked row is stated as a refusal rather than simply left out: a
 * field the model merely does not see mentioned is one it offers again next
 * round as a helpful addition, which is how a loop fails to converge.
 */
export function toFieldSelection(rows: readonly ProposalFieldRow[]): FieldSelection {
  return {
    kept: rows
      .filter(row => row.kept)
      .map(row => ({
        path: row.path,
        label: rowLabel(row),
        note: row.note?.trim() ?? ''
      })),
    dropped: rows.filter(row => !row.kept).map(row => row.path)
  }
}

/** Whether there is anything in the selection worth sending. */
export function isEmptySelection(selection: FieldSelection): boolean {
  return selection.kept.length === 0 && selection.dropped.length === 0
}

/**
 * The choices made in the last round, applied to the rows of the new one.
 *
 * Matched by path, which is the only thing stable across a reading: the model
 * may return a field with a different label, a different section, or a
 * sample value read more carefully the second time, and all of those should
 * refresh. What must not be refreshed is the part the person authored — the
 * tick, the name they gave it, the note they wrote — because losing that on
 * every round would make iterating cost more than pruning by hand.
 *
 * A path the last round never had is left exactly as the proposal offered it:
 * it is new, and nobody has had an opinion about it yet.
 */
export function carryChoices(
  rows: readonly ProposalFieldRow[],
  previous: readonly ProposalFieldRow[]
): ProposalFieldRow[] {
  const before = new Map(previous.map(row => [row.path, row]))
  return rows.map((row) => {
    const earlier = before.get(row.path)
    if (!earlier) return row
    return {
      ...row,
      kept: earlier.kept,
      renamedLabel: earlier.renamedLabel ?? null,
      note: earlier.note ?? ''
    }
  })
}

/**
 * A field the current type declares that the new reading dropped, offered as
 * a row that can be ticked back.
 *
 * Without this the removals are a verdict: a list of what is about to be lost,
 * with nothing to do about it but discard the whole regeneration. Ticked, the
 * path travels in the next round's `kept` — which is the one instruction that
 * brings a field back, since the client cannot invent the schema branch that
 * would hold it.
 */
export function rowsForRemovedPaths(
  removed: readonly string[],
  labelFor: (path: string) => string
): ProposalFieldRow[] {
  return removed.map(path => ({
    path,
    label: labelFor(path),
    sampleValue: '',
    section: null,
    role: 'context' as const,
    // Unticked on purpose: this reading did not produce the field, so leaving
    // it ticked would report as kept something no schema currently declares.
    kept: false,
    renamedLabel: null,
    note: '',
    conceptId: null,
    spineConceptId: null,
    perAccount: false,
    accountPath: null
  }))
}
