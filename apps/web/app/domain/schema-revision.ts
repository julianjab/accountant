/**
 * Reading what a regenerated configuration would change.
 *
 * A regeneration answers a complaint — "the credit-card row of this table was
 * never extracted" — and the only way to see whether it answered it is to
 * compare the fields the type declares with the ones it would declare. The
 * screen shows that before anything is written, because applying it replaces
 * the schema every future document of this kind is read with.
 *
 * Pure: the comparison is about paths, not about how they are rendered.
 */

export interface SchemaRevision {
  /** Paths the regeneration adds — what the complaint asked for, if it worked. */
  added: string[]
  /**
   * Paths that would stop being extracted.
   *
   * Shown as prominently as the additions: a mapping keyed by one of these is
   * dropped by the server when the schema is saved, so a revision that quietly
   * loses a field is a revision that quietly unconfigures part of the type.
   */
  removed: string[]
  /** Paths present on both sides, which is what keeps the mappings alive. */
  kept: string[]
}

/** What a regeneration would do to the fields the type declares. */
export function compareSchemaPaths(
  current: readonly string[],
  proposed: readonly string[]
): SchemaRevision {
  const before = new Set(current)
  const after = new Set(proposed)
  return {
    added: proposed.filter(path => !before.has(path)),
    removed: current.filter(path => !after.has(path)),
    kept: current.filter(path => after.has(path))
  }
}

/**
 * Whether a revision is worth applying at all.
 *
 * A regeneration that changes no field still rewrites the extraction prompt,
 * which is a real change the paths cannot show — so this only decides whether
 * to say "nothing changed", never whether to allow the save.
 */
export function changesNothing(revision: SchemaRevision): boolean {
  return revision.added.length === 0 && revision.removed.length === 0
}
