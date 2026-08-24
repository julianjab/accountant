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

/** Standard accounting number format: a fixed 2 decimals, grouped thousands, and a negative
 * shown as `(1.234,56)` rather than `-1.234,56` — the convention accountants read at a
 * glance, since a lone leading minus sign is easy to miss next to a column of numbers. */
export function formatAccountingNumber(value: number, locale = 'es-CO'): string {
  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Math.abs(value))
  return value < 0 ? `(${formatted})` : formatted
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
