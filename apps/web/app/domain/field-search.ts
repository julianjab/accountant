/**
 * Finding one field in a list of a hundred.
 *
 * A certificate proposes dozens of paths, and defining a type means answering
 * a question about a figure the user is looking at on the paper: "the
 * 19.586,00 line — which of these is it?". Scrolling the blocks is the answer
 * only while the document is short. Searching by what is printed on the paper
 * — the field's name, the value read from the sample, or the block heading —
 * gets there directly, and matching the path too keeps the schema addressable
 * for whoever thinks in `cuentas[].saldo`.
 *
 * Pure and shared because both screens ask it: the row that matches while
 * creating a type must be the row that matches while editing it.
 */

/**
 * Case- and accent-insensitive, so `retencion` finds "Retención".
 *
 * The whole reason to type in this box is that the label is on paper in front
 * of the user, in Spanish, with the accents a keyboard makes awkward. Failing
 * to match a word the user can plainly see would read as the field not being
 * there at all.
 */
function fold(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

/** The words a query asks for; an all-whitespace query asks for nothing. */
export function queryTerms(query: string): string[] {
  return fold(query).split(/\s+/).filter(term => term.length > 0)
}

/**
 * Whether a field answers the query, given everything the screen knows to say
 * about it.
 *
 * Every term must match — `saldo 2024` narrows rather than widens, which is
 * how a second word is meant when the first left too many rows. Terms match
 * anywhere in any part, since "586" is a fragment of a figure and "cuenta" a
 * fragment of a path, and both are how someone points at a line.
 *
 * An empty query matches everything: no filter is not an empty result.
 */
export function matchesFieldQuery(
  query: string,
  parts: readonly (string | null | undefined)[]
): boolean {
  const terms = queryTerms(query)
  if (terms.length === 0) return true
  const haystack = parts.filter(part => Boolean(part)).map(part => fold(part as string)).join(' ')
  return terms.every(term => haystack.includes(term))
}
