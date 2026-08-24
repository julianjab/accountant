/**
 * Extracted field keys come straight from a `DocumentType`'s dynamic, AI-authored JSON
 * schema (see `domain/entities/document-type.ts`) — there is no fixed set of keys to add to
 * `i18n/locales/*.json` up front, so a generic humanizer is the pragmatic choice here rather
 * than full translation coverage for AI-generated field names.
 */

const CURRENCY_LIKE_KEYWORDS = [
  'valor',
  'capital',
  'saldo',
  'interes',
  'monto',
  'ingreso',
  'egreso',
  'deuda',
  'credito',
  'pago',
  'cuota',
  'gmf',
  'retencion',
  'inflacionario',
  'costo',
  'gasto',
  'base_gravable'
]

function capitalize(word: string): string {
  return word.length > 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word
}

/** `costos_y_gastos` -> `Costos y gastos`. Sentence case (not Title Case per word) reads more
 * naturally for Spanish field names, which is the primary locale this data is extracted in. */
export function humanizeFieldKey(key: string): string {
  const words = key.split('_').filter(Boolean)
  if (words.length === 0) {
    return key
  }
  const [first, ...rest] = words
  return [capitalize(first!), ...rest].join(' ')
}

export function looksLikeCurrencyKey(key: string): boolean {
  const lower = key.toLowerCase()
  return CURRENCY_LIKE_KEYWORDS.some(keyword => lower.includes(keyword))
}

/** Standard accounting number format: a fixed 2 decimals, grouped thousands, a `$` (COP —
 * every document this app handles today is Colombian; there is no currency field on
 * `ExtractedData` to read instead), and a negative shown as `($1.234,56)` rather than
 * `-1.234,56` — the convention accountants read at a glance, since a lone leading minus sign
 * is easy to miss next to a column of numbers.
 *
 * Display-only: this never touches the stored value, only how `formatScalarValue` renders it. */
export function formatAccountingNumber(value: number, locale = 'es-CO'): string {
  // `Intl` inserts a U+00A0 (non-breaking space) between the symbol and the digits — normalized
  // to a regular space so it doesn't silently break a plain-string comparison or a copy-paste.
  const formatted = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'COP',
    currencyDisplay: 'symbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Math.abs(value)).replace(' ', ' ')
  return value < 0 ? `(${formatted})` : formatted
}

/** Groups an exact decimal *string* (never parsed to `number`) the same way as
 * `formatAccountingNumber`, but preserving every digit it was given instead of rounding to 2
 * decimal places. Used by `formatAccountingAmountString` as the fallback for a non-zero amount
 * the 2-decimal format would otherwise collapse to "$ 0,00". */
function formatFullPrecisionAmount(value: string): string {
  const negative = value.trim().startsWith('-')
  const [integerPart, fractionPart = ''] = value.replace('-', '').split('.')
  const grouped = (integerPart || '0').replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  const withSymbol = `$ ${fractionPart ? `${grouped},${fractionPart}` : grouped}`
  return negative ? `(${withSymbol})` : withSymbol
}

/** Same accounting format as `formatAccountingNumber`, for a value that arrives as an exact
 * decimal *string* (e.g. `reconciliation.ts`'s `amount`/`delta` fields, kept as strings on
 * purpose because the server computes them as `Decimal` and parsing to a JS `number` risks
 * showing a discrepancy the reconciliation engine never found).
 *
 * The 2-decimal rounding `formatAccountingNumber` applies is safe on its own, but not when it
 * would round a genuinely non-zero amount down to "$ 0,00" — a `delta` of `"0.004"` on a row
 * flagged as a mismatch would then read as reconciled, which is exactly the failure the
 * string-typed field exists to avoid. Falls back to the string's full precision in that case. */
export function formatAccountingAmountString(value: string, locale = 'es-CO'): string {
  const formatted = formatAccountingNumber(Number(value), locale)
  const collapsedToZero = Number(value) !== 0 && /^\(?\$\s*0,00\)?$/.test(formatted)
  return collapsedToZero ? formatFullPrecisionAmount(value) : formatted
}

export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isArrayOfObjects(value: unknown): value is Record<string, unknown>[] {
  return Array.isArray(value) && value.length > 0 && value.every(item => isPlainObject(item))
}

/** Renders a leaf value (never an object/array — those get their own list/table rendering). */
export function formatScalarValue(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  if (typeof value === 'number' && looksLikeCurrencyKey(key)) {
    return formatAccountingNumber(value)
  }
  return String(value)
}
