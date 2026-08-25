/**
 * Turning the configuration screen's choices into what the server stores.
 *
 * The screen edits two things that have to stay consistent with each other:
 * the extraction schema (which fields are asked of the OCR at all) and the
 * concept mapping (what those fields mean to a reconciliation model). Dropping
 * a field without dropping the mapping entry that pointed at it leaves a
 * mapping the server has to prune behind the user's back, so both sides are
 * derived here from one list of selections.
 */

import type {
  ConceptMapping,
  ConceptMappingDraft,
  ConceptMappingEntry,
  MappingChange
} from './entities/concept-mapping'
import type { DocumentTypeField, FieldRole } from './entities/document-type'
import type {
  DocumentTypeProposal,
  ProposedFieldMapping
} from './entities/document-type-proposal'
import type { SchemaField } from './extraction-schema'
import { foldLabel } from './table-rows'

/**
 * One row of the field table.
 *
 * Usually a field the schema declares. When the document prints a table — an
 * employment certificate's sixteen income lines in one repeated block — it is
 * instead *one row* of such a field, and `rowLabel` says which. Rows are peers
 * in the same flat list rather than something nested inside their field, so
 * everything the list already does for a field (searching it, grouping it under
 * the block of the page it came from, reading it top to bottom against the
 * paper) works for them unchanged.
 *
 * The two differ in exactly one way: a field can be dropped from the extraction
 * schema and a row cannot. The OCR reads the whole array or none of it, so a
 * row has no `kept` of its own — declining one means leaving it with no
 * concept, and it follows its field out of the schema when the field goes.
 */
export interface FieldSelection {
  path: string
  /**
   * The wording of the row this entry answers, as the document printed it.
   * Null on a field entry.
   *
   * This is the answer's identity: it is what the projection matches each row
   * of the document against.
   */
  rowLabel: string | null
  /** False once the user asks for the field to be dropped from the schema.
   * On a row entry this mirrors its field, and is not separately editable. */
  kept: boolean
  /** Null is a legitimate answer: the field is still extracted, it just takes
   * no part in reconciliation. */
  conceptId: string | null
  /** Which line of the base report this figure answers; null means it is
   * extracted but compared against nothing. */
  spineConceptId: string | null
  /** True when the document details each account, so the comparison is made
   * account by account instead of on the reporting party's total. */
  perAccount: boolean
  /** The field carrying the account number, without which there is no account
   * to pair against. */
  accountPath: string | null
  /**
   * On a field entry: the sibling field that says what each of its rows is,
   * set once someone answers that this field is a table. Null on an ordinary
   * field, where one answer covers every value the path reaches, and null on a
   * row entry, which *is* one of those rows.
   *
   * While it is set, the field entry carries no concept of its own — its rows
   * do — because a table has no single one.
   */
  rowLabelPath: string | null
}

/** The identity of one answer: a plain field, or one row of a table. Used
 * wherever answers have to be looked up, since a table's path is no longer
 * unique across them. */
export function selectionKey(path: string, rowLabel: string | null = null): string {
  return rowLabel === null ? path : `${path}\u0000${rowLabel}`
}

/**
 * A row as the screen may hand it back before every choice has been made.
 *
 * The three reconciliation-specific choices are optional because leaving one
 * out has to mean "unchanged", not "cleared": a caller that only edits the
 * concept must not silently drop curation it never showed.
 */
export type FieldSelectionInput
  = Pick<FieldSelection, 'path' | 'kept' | 'conceptId'>
    & Partial<Omit<FieldSelection, 'path' | 'kept' | 'conceptId'>>

/**
 * What identifies the document as a whole, rather than one figure it states.
 *
 * Each has two ways to be answered: a path, when the paper says it, and a
 * declared value, for the papers that never do. Both are carried because the
 * choice is per document type and has to survive an edit either way.
 */
export interface MappingRoles {
  reporterPath: string | null
  reporterNamePath: string | null
  periodPath: string | null
  reporterTaxId: string | null
  reporterName: string | null
  period: string | null
}

export type ConfigurationStatus = 'unusable' | 'notMapped' | 'configured'

export type MappingChangeSeverity = 'critical' | 'notice'

/**
 * The starting state of the field table.
 *
 * Everything the schema declares starts kept, because the stored schema is
 * what the OCR is already extracting: this screen is a place to trim, not a
 * blank slate the user has to re-approve field by field.
 */
export function buildFieldSelections(
  fields: SchemaField[],
  mapping: ConceptMapping | null
): FieldSelection[] {
  const entriesByPath = new Map<string, ConceptMappingEntry[]>()
  for (const entry of mapping?.entries ?? []) {
    const existing = entriesByPath.get(entry.fieldPath)
    if (existing) existing.push(entry)
    else entriesByPath.set(entry.fieldPath, [entry])
  }

  return fields.flatMap((field) => {
    const entries = entriesByPath.get(field.path) ?? []
    // A table's entries all name the same labelling field; a path with no
    // entries, or with a plain one, is the ordinary field and answers with a
    // single concept of its own.
    const rows = entries.filter(entry => entry.rowLabelPath && entry.rowLabel)
    const plain = rows.length > 0 ? undefined : entries[0]
    // How a figure is compared is a decision about the block, so a table's
    // rows share the field's answer rather than each carrying their own.
    const perAccount = entries[0]?.perAccount ?? false
    const accountPath = entries[0]?.accountPath ?? null

    const fieldEntry: FieldSelection = {
      path: field.path,
      rowLabel: null,
      kept: true,
      conceptId: plain?.conceptId ?? null,
      spineConceptId: plain?.spineConceptId ?? null,
      perAccount,
      accountPath,
      rowLabelPath: rows[0]?.rowLabelPath ?? null
    }

    return [
      fieldEntry,
      // Straight after their field, which is what keeps the list readable as
      // the paper reads: the table, then its lines.
      ...rows.map(entry => ({
        path: field.path,
        rowLabel: entry.rowLabel as string,
        kept: true,
        conceptId: entry.conceptId,
        spineConceptId: entry.spineConceptId,
        perAccount,
        accountPath,
        rowLabelPath: null
      }))
    ]
  })
}

/**
 * The same list with a row for every wording the sample document printed that
 * nobody has answered yet.
 *
 * Both halves are needed. The stored answers alone would hide a row the paper
 * states and the configuration ignores — the silence this whole feature exists
 * to end — and the document's wordings alone would drop curation for a row a
 * later sample happened not to print.
 *
 * Answers already in the list are never touched, so this can be re-run when the
 * sample's reading arrives late without undoing anything typed meanwhile.
 */
export function withRowWordings(
  selections: readonly FieldSelection[],
  wordingsFor: (rowLabelPath: string) => readonly string[]
): FieldSelection[] {
  const rowsByPath = new Map<string, FieldSelection[]>()
  for (const selection of selections) {
    if (selection.rowLabel === null) continue
    const existing = rowsByPath.get(selection.path)
    if (existing) existing.push(selection)
    else rowsByPath.set(selection.path, [selection])
  }

  return selections.flatMap((selection) => {
    if (selection.rowLabel !== null) return []
    if (selection.rowLabelPath === null) return [selection]
    const rows = rowsByPath.get(selection.path) ?? []
    const answered = new Set(rows.map(row => foldLabel(row.rowLabel)))
    return [
      selection,
      ...rows,
      ...wordingsFor(selection.rowLabelPath)
        .filter(wording => !answered.has(foldLabel(wording)))
        .map(wording => ({
          path: selection.path,
          rowLabel: wording,
          kept: selection.kept,
          conceptId: null,
          spineConceptId: null,
          perAccount: selection.perAccount,
          accountPath: selection.accountPath,
          rowLabelPath: null
        }))
    ]
  })
}

/**
 * The fields that name the rows of a block, rather than carrying a figure.
 *
 * Derived rather than flagged: a field is the label of its block exactly when
 * something in the block points at it. Storing it twice would let the two
 * drift, and a label field still offering its own concept box is a figure the
 * mapping would ask the projection to read off a column of words.
 */
export function blockLabelPaths(selections: readonly FieldSelectionInput[]): Set<string> {
  return new Set(
    selections
      .map(selection => selection.rowLabelPath)
      .filter((path): path is string => Boolean(path))
  )
}

/**
 * The list with one more row on a table, named as the reader typed it.
 *
 * The sample's own reading fills this list in almost every case, but it cannot
 * be the only way in: a type configured before extractions were kept, or from a
 * document whose reading was never stored, would otherwise reach "each row is
 * different" with nothing to answer and no way to get there.
 */
export function addRow(
  selections: readonly FieldSelection[],
  path: string,
  rowLabel: string
): FieldSelection[] {
  const label = rowLabel.trim()
  const field = selections.find(
    selection => selection.path === path && selection.rowLabel === null
  )
  if (label === '' || !field?.rowLabelPath) return [...selections]
  const folded = foldLabel(label)
  const exists = selections.some(
    selection => selection.path === path && foldLabel(selection.rowLabel) === folded
  )
  if (exists) return [...selections]

  const lastOfField = selections.reduce(
    (found, selection, index) => (selection.path === path ? index : found),
    -1
  )
  const inserted = [...selections]
  inserted.splice(lastOfField + 1, 0, {
    path,
    rowLabel: label,
    kept: field.kept,
    conceptId: null,
    spineConceptId: null,
    perAccount: field.perAccount,
    accountPath: field.accountPath,
    rowLabelPath: null
  })
  return inserted
}

/** The list without one row of a table, and without the answer it held. */
export function removeRow(
  selections: readonly FieldSelection[],
  path: string,
  rowLabel: string
): FieldSelection[] {
  return selections.filter(
    selection => !(selection.path === path && selection.rowLabel === rowLabel)
  )
}

/**
 * The list after answering, for one field, whether each of its rows says what
 * it is.
 *
 * Turning it on loads the rows from the paper; turning it off drops them along
 * with the per-row curation they held, which is the honest consequence — those
 * answers describe rows nothing is telling apart any more.
 */
export function setRowLabelPath(
  selections: readonly FieldSelection[],
  path: string,
  rowLabelPath: string | null,
  wordingsFor: (rowLabelPath: string) => readonly string[]
): FieldSelection[] {
  const updated = selections.flatMap((selection) => {
    if (selection.path !== path) return [selection]
    // Rows of the field being re-answered: dropped either way, and rebuilt
    // below when the field is still a table.
    if (selection.rowLabel !== null) return []
    return [
      {
        ...selection,
        rowLabelPath,
        // A table has no single concept, so a leftover field-level answer would
        // sit there contradicting its rows.
        conceptId: rowLabelPath === null ? selection.conceptId : null,
        spineConceptId: rowLabelPath === null ? selection.spineConceptId : null
      }
    ]
  })
  return withRowWordings(updated, wordingsFor)
}

/**
 * The paths that stay in the extraction schema.
 *
 * Read off the field entries alone. A row is not a field the OCR can be asked
 * for separately — the array is read whole or not at all — so its own `kept`
 * only ever mirrors its field's, and reading it here would let a stale mirror
 * decide what the schema contains.
 */
export function keptPaths(selections: readonly FieldSelectionInput[]): Set<string> {
  return new Set(
    selections
      .filter(selection => selection.kept && (selection.rowLabel ?? null) === null)
      .map(selection => selection.path)
  )
}

/** An answer the screen did not give falls back to what was already stored, so
 * a control the screen never showed cannot clear curation behind the user. */
function chosen<T>(explicit: T | undefined, previous: T | undefined, fallback: T): T {
  if (explicit !== undefined) return explicit
  return previous ?? fallback
}

/**
 * The mapping to store for the selections as they stand.
 *
 * `sign` is carried over from the entry that already described the same field:
 * it is curation this screen has no control for, and rebuilding an entry from
 * scratch would quietly flip a certificate configured to state its figures with
 * the opposite sign.
 */
export function toMappingDraft(
  selections: readonly FieldSelectionInput[],
  roles: MappingRoles,
  // A draft, not only a stored mapping: the create flow has curation to carry
  // over (the proposal's signs and account paths) that was never stored yet.
  existing: ConceptMappingDraft | null
): ConceptMappingDraft {
  const kept = keptPaths(selections)
  const previousByKey = new Map(
    (existing?.entries ?? []).map(entry => [
      selectionKey(entry.fieldPath, entry.rowLabel ?? null),
      entry
    ])
  )
  // The field entry's own curation, which its rows share: how a figure is
  // compared, and which field says what each row is, are decisions about the
  // block rather than about one line of it.
  const fieldByPath = new Map(
    selections
      .filter(selection => (selection.rowLabel ?? null) === null)
      .map(selection => [selection.path, selection])
  )
  const labels = blockLabelPaths(selections)

  const entries: ConceptMappingEntry[] = selections.flatMap((selection) => {
    const rowLabel = selection.rowLabel ?? null
    const field = fieldByPath.get(selection.path)
    const rowLabelPath = field?.rowLabelPath ?? null

    // A field entry that declares a table is not an entry itself: its rows
    // are. Emitting one here would claim every row of the table at once,
    // filing sixteen different figures under a single concept.
    if (rowLabel === null && rowLabelPath !== null) return []
    // The column of words that tells the rows apart is not a figure. It is
    // still extracted — the projection needs it to match on — but mapping it
    // would ask the engine to read an amount off a wording.
    if (labels.has(selection.path)) return []
    // A row whose field was trimmed away, or whose labelling field was. The
    // second must not fall back to an undiscriminated entry: that is the same
    // over-claim, arrived at by a different route.
    if (rowLabel !== null && !kept.has(rowLabelPath ?? '')) return []
    if (!selection.kept || !kept.has(selection.path)) return []
    if (!selection.conceptId) return []

    const claimed = chosen(field?.accountPath, previousByKey.get(selection.path)?.accountPath, null)
    // A trimmed field cannot name an account any more than it can carry an
    // amount, so a stale account path is dropped rather than sent back.
    const accountPath = claimed && kept.has(claimed) ? claimed : null
    const previous = previousByKey.get(selectionKey(selection.path, rowLabel))

    return [
      {
        fieldPath: selection.path,
        conceptId: selection.conceptId,
        accountPath,
        // Carried over from the entry that already described the same answer:
        // it is curation this screen has no control for, and rebuilding an
        // entry from scratch would quietly flip a certificate configured to
        // state its figures with the opposite sign.
        sign: previous?.sign ?? 1,
        spineConceptId: chosen(selection.spineConceptId, previous?.spineConceptId, null),
        // Comparing account by account when this side names no account pairs
        // every certified figure against nothing, which reports a figure the
        // document does state as missing. A total is the answer that at least
        // compares something.
        perAccount:
          chosen(field?.perAccount, previousByKey.get(selection.path)?.perAccount, false)
          && accountPath !== null,
        rowLabelPath: rowLabel === null ? null : rowLabelPath,
        rowLabel
      }
    ]
  })

  const rolePath = (path: string | null) => (path && kept.has(path) ? path : null)

  return {
    entries,
    reporterPath: rolePath(roles.reporterPath),
    reporterNamePath: rolePath(roles.reporterNamePath),
    periodPath: rolePath(roles.periodPath),
    // Not filtered by the kept fields: a declared value is not read from the
    // document at all, so trimming the schema cannot invalidate it.
    reporterTaxId: blankToNull(roles.reporterTaxId),
    reporterName: blankToNull(roles.reporterName),
    period: blankToNull(roles.period)
  }
}

/** An emptied text input means "not declared", not "declared as nothing". */
function blankToNull(value: string | null): string | null {
  const trimmed = value?.trim() ?? ''
  return trimmed === '' ? null : trimmed
}

/**
 * Whether the type actually reconciles anything.
 *
 * Entries with nobody to attribute them to are the trap this screen exists
 * to close: the server stores them happily and then discards every fact
 * they produce, so that state is reported as unusable, not configured.
 */
export function configurationStatus(draft: ConceptMappingDraft): ConfigurationStatus {
  if (draft.entries.length === 0) return 'notMapped'
  // Either answer attributes the figures: the paper states the party, or the
  // type declares it. Neither is what makes the mapping produce nothing.
  if (!draft.reporterPath && !draft.reporterTaxId) return 'unusable'
  return 'configured'
}

/** A mapping this screen would refuse to save, because saving it would make the
 * type look configured while producing nothing. */
export function isDraftSavable(draft: ConceptMappingDraft): boolean {
  return configurationStatus(draft) !== 'unusable'
}

/** Whether sending this draft is worth a request at all: an empty draft for a
 * type that was never mapped would only create an empty record. */
export function shouldSaveDraft(draft: ConceptMappingDraft, existing: ConceptMapping | null): boolean {
  if (existing) return true
  return (
    draft.entries.length > 0
    || draft.reporterPath !== null
    || draft.periodPath !== null
    || draft.reporterTaxId !== null
    || draft.period !== null
  )
}

/**
 * How loudly a consequence of a schema edit has to be reported.
 *
 * `mapping_cleared` means the type stopped reconciling entirely and
 * `prune_failed` means the server could not tell what state the mapping is in;
 * both need the user back on this screen, whereas a single dropped entry is
 * the expected outcome of trimming a field.
 */
export function mappingChangeSeverity(change: MappingChange): MappingChangeSeverity {
  return change.change === 'mapping_cleared' || change.change === 'prune_failed'
    ? 'critical'
    : 'notice'
}

/**
 * The fields answering one line of the base report.
 *
 * Grouping is the whole point of the spine choice: the engine adds up every
 * amount mapped to the same line before comparing it, which is how a debt the
 * base report states once and the certificate splits into capital, interest and
 * charges is expressed without anyone writing a formula. A screen that listed
 * these four fields separately would never let that be discovered.
 */
export interface SpineGroup {
  /** Null gathers everything that answers no line: dropped fields, fields with
   * no concept, and concepts left uncompared on purpose. */
  spineConceptId: string | null
  /** One `selectionKey` per answer feeding this line. Keys rather than paths
   * because a table's rows share a path and answer different lines — the very
   * case where knowing what is summed matters most. */
  keys: string[]
  /** More than one field feeds this line, so the comparison is made on a sum. */
  summed: boolean
  /** Part of the sum is stated account by account and part as a total, so the
   * two halves cannot be added up into one comparable figure. */
  mixedComparison: boolean
}

/** One answer the comparison will read: a plain field, or one row of a table. */
interface SpineMember {
  key: string
  spineConceptId: string | null
  perAccount: boolean
}

/**
 * What one entry of the list contributes to the comparison.
 *
 * A field entry that declares a table contributes nothing of its own — its rows
 * are the answers — so it is filed under "answers no line", where it does not
 * inflate the sum its rows are counted in.
 */
function spineMemberOf(selection: FieldSelectionInput): SpineMember {
  const rowLabel = selection.rowLabel ?? null
  const declaresATable = rowLabel === null && Boolean(selection.rowLabelPath)
  const answers = selection.kept && !declaresATable && Boolean(selection.conceptId)
  return {
    key: selectionKey(selection.path, rowLabel),
    spineConceptId: answers ? (selection.spineConceptId ?? null) : null,
    perAccount: selection.perAccount === true
  }
}

/**
 * The field table arranged the way the comparison will read it.
 *
 * Groups keep the order in which their first field appears, so rearranging the
 * table never reorders under the reader; the unanswered group goes last because
 * it is the leftovers, not a line of the report.
 */
export function groupBySpineConcept(selections: readonly FieldSelectionInput[]): SpineGroup[] {
  const groups = new Map<string | null, SpineMember[]>()

  for (const member of selections.map(spineMemberOf)) {
    const members = groups.get(member.spineConceptId)
    if (members) members.push(member)
    else groups.set(member.spineConceptId, [member])
  }

  const unanswered = groups.get(null)
  groups.delete(null)
  if (unanswered) groups.set(null, unanswered)

  return [...groups].map(([spineConceptId, members]) => ({
    spineConceptId,
    keys: members.map(member => member.key),
    summed: spineConceptId !== null && members.length > 1,
    mixedComparison:
      spineConceptId !== null
      && members.some(member => member.perAccount)
      && members.some(member => !member.perAccount)
  }))
}

/**
 * The fields claiming an account-by-account comparison without naming the
 * account.
 *
 * `toMappingDraft` downgrades these to a total rather than storing a comparison
 * that can only ever fail, and the screen has to say so: from the user's side
 * the difference is between a certificate that lists each account and one that
 * states a single figure, and only they can see which one they are holding.
 */
export function fieldsMissingAccountPath(
  selections: readonly FieldSelectionInput[]
): string[] {
  // Mirrors the screen's own v-if for the comparison controls: without a spine concept the
  // "total vs. per-account" question isn't even shown, so a selection that lands here with
  // perAccount still true (e.g. the user answered it, then cleared the spine concept) can't
  // be fixed from the UI — it must not count as "missing", or the warning it prints below
  // would stay stuck on forever with no control on screen to clear it.
  // Reported on the field, once, however many rows it has: the comparison is a
  // decision about the block, and the control that would fix it sits there.
  return [...pathsAnsweringALine(selections)].filter((path) => {
    const field = selections.find(
      selection => selection.path === path && (selection.rowLabel ?? null) === null
    )
    return Boolean(field?.kept && field.perAccount === true && !field.accountPath)
  })
}

/**
 * The fields that feed a line of the base report — through their own answer, or
 * through any row of their table.
 *
 * Mirrors the screen's own gate on the comparison controls: without a line
 * answered, the "total vs. per-account" question is not even shown, so a field
 * that reached `perAccount === true` and can no longer be corrected must not
 * count as missing anything.
 */
export function pathsAnsweringALine(
  selections: readonly FieldSelectionInput[]
): Set<string> {
  const answering = new Set<string>()
  for (const selection of selections) {
    if (!selection.kept || !selection.conceptId || !selection.spineConceptId) continue
    // A field entry declaring a table answers through its rows, never itself.
    if ((selection.rowLabel ?? null) === null && selection.rowLabelPath) continue
    answering.add(selection.path)
  }
  return answering
}

/* ------------------------------------------------------------------ *
 * Creating a type from a proposal
 *
 * The same two questions as above — which fields to keep, and who reports
 * them — asked before anything exists on the server. The rules are shared
 * with the configuration screen on purpose: a type created here must not be
 * able to reach a state that screen considers impossible.
 * ------------------------------------------------------------------ */

/** A proposed field with the user's decision on it, shaped so every helper
 * above accepts it unchanged. */
export interface ProposalFieldRow extends FieldSelection {
  label: string
  sampleValue: string
  /** Null for a field the proposal filed under no heading. */
  section: string | null
  role: FieldRole
  /** What the person renamed this field to, null while it is still called
   * whatever the document calls it. Kept apart from `label` so a regeneration
   * can refresh the document's own wording without overwriting theirs — and
   * so the next round can be told which of the two the model is looking at. */
  renamedLabel?: string | null
  /** A correction aimed at this field alone ("this is a row of the table, not
   * the total"), sent with it on the next round. Empty for the ordinary field
   * nobody had to explain. */
  note?: string
}

/** What to call a field: the person's word for it when they gave one. */
export function rowLabel(row: ProposalFieldRow): string {
  return row.renamedLabel?.trim() || row.label
}

/**
 * Whether a field starts selected.
 *
 * "Muchas veces de un documento sólo quiero obtener la identificación y los
 * valores importantes o totales": the identification and the amounts are what
 * the paper is kept for, so the starting selection is already close to the
 * answer and the work left is correcting it, not building it.
 */
export function isKeptByDefault(role: FieldRole): boolean {
  return role !== 'context'
}

/** The proposal's mappings read as a draft, so the curation it already did
 * (which concept, which account, which sign) survives the trimming. */
export function proposalMappingBaseline(proposal: DocumentTypeProposal): ConceptMappingDraft {
  return {
    entries: proposal.fieldMappings.map(mapping => ({
      fieldPath: mapping.fieldPath,
      conceptId: mapping.conceptId,
      accountPath: mapping.accountPath,
      sign: mapping.sign,
      // None of these is proposed: which line of the base report a figure
      // answers, whether it is compared account by account, and whether the
      // field is a table whose rows each mean something different, are all
      // decided on the configuration screen once the type exists.
      spineConceptId: null,
      perAccount: false,
      rowLabelPath: null,
      rowLabel: null
    })),
    reporterPath: proposal.reporterPath,
    reporterNamePath: proposal.reporterNamePath,
    periodPath: proposal.periodPath,
    // Never proposed: the model reads the paper, and these exist precisely for
    // what the paper does not say.
    reporterTaxId: null,
    reporterName: null,
    period: null
  }
}

/**
 * The rows to put in front of the user.
 *
 * Fields the schema declares but the proposal forgot to describe are listed
 * too, and start selected: the schema is already asking the OCR for them, and
 * dropping data on the strength of a gap in the proposal's own list would be a
 * silent loss. They carry no heading, so they gather at the end.
 */
export function buildProposalRows(
  proposal: DocumentTypeProposal,
  schemaFields: readonly SchemaField[]
): ProposalFieldRow[] {
  const mappingByPath = new Map(
    proposal.fieldMappings.map(mapping => [mapping.fieldPath, mapping])
  )

  const buildRow = (
    path: string,
    label: string,
    role: FieldRole,
    sampleValue: string,
    section: string | null,
    kept: boolean
  ): ProposalFieldRow => {
    const mapping = mappingByPath.get(path)
    return {
      path,
      label,
      role,
      sampleValue,
      section,
      kept,
      conceptId: mapping?.conceptId ?? null,
      accountPath: mapping?.accountPath ?? null,
      spineConceptId: null,
      perAccount: false,
      rowLabelPath: null,
      rowLabel: null
    }
  }

  const described = new Set(proposal.fields.map(field => field.path))
  // A proposal that described some fields and missed one is a gap: the schema
  // is already asking the OCR for that field, and dropping it over an omission
  // in a list the model wrote would be a silent loss. A proposal that
  // described *nothing* is not a gap — it is the whole screen — and ticking
  // thirty-five fields there hands the user a list to undo by hand.
  const describedNothing = proposal.fields.length === 0
  const rows = proposal.fields.map(field =>
    buildRow(
      field.path,
      field.label || field.path,
      field.role,
      field.sampleValue,
      field.section || null,
      isKeptByDefault(field.role)
    )
  )

  for (const field of schemaFields) {
    if (described.has(field.path)) continue
    // Read off the schema rather than defaulted. The schema is required and
    // always present; the proposal's description list is neither, and when it
    // came back empty this fallback produced the screen it was meant to
    // replace — every field named by its path, every one classified as
    // context, every one ticked, no blocks at all.
    rows.push(
      buildRow(
        field.path,
        schemaLabel(field),
        schemaRole(field),
        '',
        schemaSection(field.path),
        describedNothing ? isKeptByDefault(schemaRole(field)) : true
      )
    )
  }

  return rows
}

/** What the schema itself says a field is called. Its `description` is a
 * sentence about the value, which reads better than the property name. */
function schemaLabel(field: SchemaField): string {
  return field.description || field.name
}

const IDENTIFIER_NAME = /nit|identificacion|identification|documento|cuenta|numero|number/i

/**
 * What a field holds, inferred from the schema.
 *
 * A guess, and a cheap one, but the alternative in place was calling every
 * field context — which starts the whole document unticked or, as it was,
 * ticked with nothing distinguishing the figures from the letterhead. The
 * user corrects this in one click; they cannot correct thirty-five.
 */
function schemaRole(field: SchemaField): FieldRole {
  if (field.type === 'number' || field.type === 'integer') return 'amount'
  if (IDENTIFIER_NAME.test(field.name)) return 'identifier'
  return 'context'
}

/**
 * The block a field belongs to, taken from the object that contains it.
 *
 * A schema nests its figures under a heading of its own —
 * `otra_informacion_tributaria.cuenta_ahorros` — and that nesting is the
 * document's own grouping, recorded without anyone being asked for it.
 */
function schemaSection(path: string): string | null {
  const cut = path.lastIndexOf('.')
  if (cut < 0) return null
  const parent = path.slice(0, cut)
  return parent.replace(/\[\]/g, '') || null
}

/** The proposed fields under one heading of the document. */
export interface SectionGroup {
  /** Null gathers the fields that sit under no heading. */
  section: string | null
  paths: string[]
  keptCount: number
}

/**
 * The rows arranged the way the paper reads.
 *
 * Sections keep the order in which they first appear, so the list matches the
 * document the user is holding rather than an alphabetical index; the headless
 * group goes last because it is the leftovers, not a part of the document.
 */
export function groupBySection(rows: readonly ProposalFieldRow[]): SectionGroup[] {
  const groups = new Map<string | null, ProposalFieldRow[]>()

  for (const row of rows) {
    const members = groups.get(row.section)
    if (members) members.push(row)
    else groups.set(row.section, [row])
  }

  const headless = groups.get(null)
  groups.delete(null)
  if (headless) groups.set(null, headless)

  return [...groups].map(([section, members]) => ({
    section,
    paths: members.map(member => member.path),
    keptCount: members.filter(member => member.kept).length
  }))
}

/** What stops the type from being created. */
export type CreationBlock = 'noFields' | 'noReporter'

/**
 * Whether the draft may be created at all.
 *
 * The reporter rule is the configuration screen's, restated before the type
 * exists: mappings with nobody to attribute their amounts to are discarded by
 * the server, and the type would then report every figure it should back as
 * missing. A type with no fields is refused too — it would ask the OCR for
 * nothing and file an empty answer for every document of its kind.
 */
export function creationBlock(
  rows: readonly ProposalFieldRow[],
  draft: ConceptMappingDraft
): CreationBlock | null {
  if (keptPaths(rows).size === 0) return 'noFields'
  if (!isDraftSavable(draft)) return 'noReporter'
  return null
}

/**
 * The descriptions to store for the fields.
 *
 * Without them the type keeps only paths, and the sections the user just chose
 * by would be gone the moment this screen is left — which would make the
 * choosing itself pointless.
 *
 * By default this covers every row the reading identified, including the ones
 * left unticked: those stay in the type's candidate schema so they can be
 * ticked back later, and a field can only be offered to someone by name. Pass
 * `keptOnly` for the callers that describe what is extracted and nothing else.
 */
export function toDocumentTypeFields(
  rows: readonly ProposalFieldRow[],
  options: { keptOnly?: boolean } = {}
): DocumentTypeField[] {
  const included = options.keptOnly ? rows.filter(row => row.kept) : rows
  return included
    .map(row => ({
      path: row.path,
      label: rowLabel(row),
      role: row.role,
      section: row.section ?? '',
      // Carried so the editor can show the same value the row was chosen by;
      // recomputing it later would mean re-reading the paper.
      sampleValue: row.sampleValue ?? ''
    }))
}

/** The draft's entries as the create endpoint takes them: it stores what it is
 * sent, and the two curated columns it has no place for are set later. */
export function toProposedFieldMappings(draft: ConceptMappingDraft): ProposedFieldMapping[] {
  return draft.entries.map(entry => ({
    fieldPath: entry.fieldPath,
    conceptId: entry.conceptId,
    accountPath: entry.accountPath,
    sign: entry.sign
  }))
}

function tokenizeYears(text: string): string[] {
  return text
    .split(/[\s,;]+/)
    .map(token => token.trim())
    .filter(token => token.length > 0)
}

function isYear(token: string): boolean {
  return /^\d{4}$/.test(token)
}

/**
 * The years typed into the tax-year box.
 *
 * Free text rather than a picker because the useful answer is almost always
 * "any year" — an empty list — and, when it is not, it is one or two years the
 * user already knows.
 */
export function parseTaxYears(text: string): number[] {
  const years = tokenizeYears(text).filter(isYear).map(Number)
  return [...new Set(years)].sort((a, b) => a - b)
}

/** Anything that is not a four-digit year, reported rather than silently
 * dropped: a typo that quietly narrows a type to no year at all would take a
 * failed reconciliation to notice. */
export function invalidTaxYears(text: string): string[] {
  return tokenizeYears(text).filter(token => !isYear(token))
}

/**
 * One answer to "where does this come from", written as one string.
 *
 * Two separate controls — a dropdown of paths and a text box beside it —
 * asked the user to know the difference between a path and a value before
 * they had a reason to care about it, and left the screen with two places to
 * look for one answer. One box, offering the paths it knows and accepting
 * anything else, asks the question the way a person asks it: what fills this,
 * a field of the document or a value I am telling you?
 */
export interface SourceAnswer {
  /** The chosen path, when what was typed names a field of this document. */
  path: string | null
  /** The declared value, when it does not. */
  value: string | null
}

export function readSource(answer: string | null, knownPaths: readonly string[]): SourceAnswer {
  const text = answer?.trim() ?? ''
  if (text === '') return { path: null, value: null }
  // A path wins whenever the text names one. Someone who types `issuer_nit`
  // means the field, not the literal characters — and the two readings differ
  // wildly: one reads the paper, the other attributes every document to a
  // party called "issuer_nit".
  if (knownPaths.includes(text)) return { path: text, value: null }
  return { path: null, value: text }
}

/** The single string that shows both answers, for binding to one control. */
export function writeSource(path: string | null, value: string | null): string {
  return path ?? value ?? ''
}
