/**
 * Laying extracted fields out the way the document lays them out.
 *
 * A certificate is not a flat list of values. It is divided into blocks on
 * paper — the issuer's details, then withholdings, then balances — and a
 * reader who knows the document finds a figure by knowing which block it is
 * in. The extraction schema loses that: it keeps a path and a JSON type, so
 * every screen reading it back showed one undifferentiated column of
 * `cuentas[].saldo`.
 *
 * The AI names those blocks when it proposes a type, and the type stores what
 * it named. These rules are how a screen gets back to the shape of the page.
 * They are pure so the configurator and the document detail group identically
 * — a field that sits under "Retenciones" while choosing it must sit under
 * "Retenciones" when reading its value, or the two screens are describing
 * different documents.
 */

import type { DocumentTypeField } from '~/domain/entities/document-type'

export interface Section<T> {
  /** The document's own name for this block; empty for the unnamed group. */
  name: string
  items: T[]
}

/**
 * The top-level key a path belongs to: `cuentas[].saldo` lives under
 * `cuentas`.
 *
 * Extracted data arrives keyed by top-level property, while descriptions name
 * leaves several levels down. Without this the two never meet, and a document
 * whose figures are all inside one array would show no sections at all.
 */
export function rootKey(path: string): string {
  const [first = ''] = path.split('.')
  return first.endsWith('[]') ? first.slice(0, -2) : first
}

/**
 * What the document calls this path, or the path itself when nothing does.
 *
 * Falling back to the path rather than to an empty string on purpose: a row
 * with no label at all is unreadable, while a row labelled `gmf` is merely
 * unpolished, and types created before descriptions existed have no labels.
 */
export function labelFor(path: string, fields: readonly DocumentTypeField[]): string {
  return fields.find(field => field.path === path)?.label || path
}

/**
 * Which block of the document a path sits in, empty when unknown.
 *
 * An exact match wins; otherwise the section of any described field under the
 * same top-level key is used, which is what places a whole extracted array
 * under the heading its own columns were given.
 */
export function sectionFor(path: string, fields: readonly DocumentTypeField[]): string {
  const exact = fields.find(field => field.path === path)
  if (exact) return exact.section
  const root = rootKey(path)
  return fields.find(field => field.section && rootKey(field.path) === root)?.section ?? ''
}

/**
 * Groups items into sections, in the order the type declares them.
 *
 * Declaration order is the document's own order, which is the only order an
 * accountant can check a page against — sorting alphabetically would scatter
 * a certificate's blocks. Anything with no section falls into a single
 * trailing unnamed group rather than being dropped, so nothing extracted
 * disappears from the screen because the AI declined to name its block.
 */
export function groupBySection<T>(
  items: readonly T[],
  pathOf: (item: T) => string,
  fields: readonly DocumentTypeField[]
): Section<T>[] {
  const order = orderedSectionNames(fields)
  const grouped = new Map<string, T[]>(order.map(name => [name, []]))
  const unsectioned: T[] = []

  for (const item of items) {
    const name = sectionFor(pathOf(item), fields)
    if (!name) {
      unsectioned.push(item)
      continue
    }
    const bucket = grouped.get(name)
    if (bucket) bucket.push(item)
    else grouped.set(name, [item])
  }

  const sections = [...grouped]
    .filter(([, bucket]) => bucket.length > 0)
    .map(([name, bucket]) => ({ name, items: bucket }))

  if (unsectioned.length > 0) sections.push({ name: '', items: unsectioned })
  return sections
}

/** The distinct section names a type declares, first appearance first. */
export function orderedSectionNames(fields: readonly DocumentTypeField[]): string[] {
  const seen: string[] = []
  for (const field of fields) {
    if (field.section && !seen.includes(field.section)) seen.push(field.section)
  }
  return seen
}

/**
 * Whether grouping would tell the reader anything.
 *
 * One section wrapping every field is a heading that separates nothing, and
 * no section at all is the older types. Both render better flat, so a screen
 * asks this rather than showing a lone decorative header.
 */
export function hasUsefulSections(fields: readonly DocumentTypeField[]): boolean {
  return orderedSectionNames(fields).length > 1
}

/**
 * Whether a label says anything the path does not already say.
 *
 * A type whose proposal came back with no descriptions falls back to the
 * schema, which labels each field with its own property name — `nit` for
 * `agente_retenedor.nit`. That is a label in the data and no label on screen,
 * and treating it as one is what left those types stuck: nothing was missing,
 * so nothing offered to fill it.
 */
function saysNothing(label: string, path: string): boolean {
  return !label || label === path || label === path.split('.').pop()?.replace('[]', '')
}

/** Whether re-reading the paper could still tell us something about a field. */
export function isUnderdescribed(field: DocumentTypeField): boolean {
  return saysNothing(field.label, field.path) || !field.section || !field.sampleValue
}

/**
 * Stored descriptions, filled in from a fresh reading of the same paper.
 *
 * Additive on purpose. A stored description was written when the type was
 * configured and may well have been corrected by hand since; a recovered one
 * comes from re-reading the paper today. Where both say something the stored
 * one is the curated answer and wins.
 *
 * Per attribute, not per field. Merging whole fields meant a field that had a
 * name but no sample value — every type saved before values were carried —
 * could never gain one: its path was present, so the re-read that had just
 * read the value off the paper was discarded entire. An empty attribute has
 * no curation to protect.
 *
 * The wholesale part still matters because the server replaces descriptions
 * wholesale: sending only what a re-read matched would delete every label it
 * failed to match, which on a well-described type is a straight loss of
 * curated data caused by an action offering to add to it.
 */
export function mergeDescriptions(
  stored: readonly DocumentTypeField[],
  recovered: readonly DocumentTypeField[]
): DocumentTypeField[] {
  const freshByPath = new Map(recovered.map(field => [field.path, field]))
  const merged = stored.map((field) => {
    const fresh = freshByPath.get(field.path)
    if (!fresh) return field
    return {
      ...field,
      label: saysNothing(field.label, field.path) ? fresh.label : field.label,
      section: field.section || fresh.section,
      sampleValue: field.sampleValue || fresh.sampleValue
    }
  })
  const described = new Set(stored.map(field => field.path))
  return [...merged, ...recovered.filter(field => !described.has(field.path))]
}

/**
 * The descriptions from a fresh proposal that a stored schema can actually use.
 *
 * Types configured before descriptions were stored have none, which leaves
 * their configurator a list of dotted paths forever. Re-reading the sample
 * recovers the labels and blocks without touching the prompt, the schema or
 * the mappings someone curated.
 *
 * Only paths the stored schema already declares survive. A fresh run of the
 * model over the same paper invents its own field names, and it does not have
 * to agree with the run that produced the stored schema — a description for
 * `saldo_final` when the schema says `saldo` would name a field that is never
 * extracted, and would read on screen as a field that exists.
 *
 * That same disagreement is why this can legitimately recover very little:
 * the caller is expected to say how many matched rather than report success.
 */
export function descriptionsForKnownPaths(
  proposed: readonly DocumentTypeField[],
  knownPaths: readonly string[]
): DocumentTypeField[] {
  const known = new Set(knownPaths)
  return proposed.filter(field => known.has(field.path))
}
