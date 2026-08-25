/**
 * Reading a document that prints a table, not labelled boxes.
 *
 * An employment certificate states its income in one repeated block: each row
 * says what it is ("Pagos por salarios") and how much. The configuration screen
 * has to answer one question per row, not one per field — and the only place
 * the rows actually exist is the sample document the type was read from.
 */

/**
 * Fold a wording down to what two documents can be compared on.
 *
 * Mirrors `reconciliation/core/text.py::fold` on the server, which is what the
 * projection matches on. If the screen folded differently, a row the user
 * answered here would silently fail to match the same row at projection time.
 */
export function foldLabel(text: string | null | undefined): string {
  return (text ?? '')
    .normalize('NFKD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

/**
 * The wordings a repeated field actually printed, in the order the paper
 * printed them.
 *
 * Deduplicated by the folded form but reported as first written: two rows a
 * reader would call the same row are one question, and the answer is stored
 * under the wording the document used.
 */
export function distinctRowWordings(fields: unknown, path: string): string[] {
  const seen = new Set<string>()
  const wordings: string[] = []
  for (const value of resolveAll(fields, path)) {
    if (typeof value !== 'string' && typeof value !== 'number') continue
    const text = String(value).trim()
    const folded = foldLabel(text)
    if (folded === '' || seen.has(folded)) continue
    seen.add(folded)
    wordings.push(text)
  }
  return wordings
}

/** Every value a dotted path reaches, walking `[]` segments. The runtime twin
 * of the server's `_walk`, kept deliberately small: this only ever reads row
 * wordings, never amounts. */
function resolveAll(node: unknown, path: string): unknown[] {
  const segments = path.split('.').filter(segment => segment !== '')
  return walk(node, segments)
}

function walk(node: unknown, segments: readonly string[]): unknown[] {
  if (segments.length === 0) return [node]
  const [segment, ...rest] = segments as [string, ...string[]]
  const iterate = segment.endsWith('[]')
  const key = iterate ? segment.slice(0, -2) : segment

  let current = node
  if (key !== '') {
    if (typeof current !== 'object' || current === null || Array.isArray(current)) return []
    if (!(key in current)) return []
    current = (current as Record<string, unknown>)[key]
  }
  if (!iterate) return walk(current, rest)
  if (!Array.isArray(current)) return []
  return current.flatMap(item => walk(item, rest))
}

/** The `[]` prefix a path sits under, or null when it is not inside a list. */
export function listPrefixOf(path: string): string | null {
  const cut = path.lastIndexOf('[]')
  return cut < 0 ? null : path.slice(0, cut + 2)
}

/** The fields that could say what each row of `path`'s table is: its siblings
 * inside the same repeated block, and never the field itself — an amount
 * cannot label the row it sits on. */
export function rowLabelCandidates(path: string, allPaths: readonly string[]): string[] {
  const prefix = listPrefixOf(path)
  if (prefix === null) return []
  return allPaths.filter(
    candidate => candidate !== path && listPrefixOf(candidate) === prefix
  )
}
