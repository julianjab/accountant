import { describe, expect, it } from 'vitest'
import {
  formatAccountingAmountString,
  formatAccountingNumber,
  formatSampleAmount,
  formatScalarValue,
  humanizeFieldKey,
  isArrayOfObjects,
  isPlainObject,
  looksLikeCurrencyKey
} from '~/utils/extraction-field-display'

describe('humanizeFieldKey', () => {
  it('turns snake_case into sentence case', () => {
    expect(humanizeFieldKey('costos_y_gastos')).toBe('Costos y gastos')
    expect(humanizeFieldKey('agente_retenedor')).toBe('Agente retenedor')
    expect(humanizeFieldKey('anio_gravable')).toBe('Anio gravable')
  })

  it('leaves a single word capitalized', () => {
    expect(humanizeFieldKey('gmf')).toBe('Gmf')
  })
})

describe('looksLikeCurrencyKey', () => {
  it('flags keys that read as monetary', () => {
    expect(looksLikeCurrencyKey('valor')).toBe(true)
    expect(looksLikeCurrencyKey('saldo_disponible')).toBe(true)
    expect(looksLikeCurrencyKey('base_gravable')).toBe(true)
  })

  it('does not flag unrelated keys', () => {
    expect(looksLikeCurrencyKey('contribuyente')).toBe(false)
    expect(looksLikeCurrencyKey('fecha_expedicion')).toBe(false)
  })
})

describe('formatAccountingNumber', () => {
  it('groups thousands, fixes two decimals, and prefixes the COP symbol for the es-CO locale', () => {
    expect(formatAccountingNumber(9946131)).toBe('$ 9.946.131,00')
  })

  it('wraps a negative value in parentheses instead of a leading minus', () => {
    expect(formatAccountingNumber(-1234.5)).toBe('($ 1.234,50)')
  })
})

describe('formatAccountingAmountString', () => {
  it('formats a plain decimal string like formatAccountingNumber', () => {
    expect(formatAccountingAmountString('146231584.00')).toBe('$ 146.231.584,00')
    expect(formatAccountingAmountString('-145220676.00')).toBe('($ 145.220.676,00)')
  })

  // Regression: reconciliation.ts keeps amounts as exact decimal strings specifically because
  // parsing them risks showing a discrepancy the engine never found. Rounding "0.004" to two
  // decimals gives "$ 0,00" — on a row flagged as a mismatch, that reads as reconciled, which
  // is exactly the failure the string-typed field exists to prevent.
  it('falls back to full precision instead of rounding a non-zero delta down to zero', () => {
    expect(formatAccountingAmountString('0.004')).toBe('$ 0,004')
    expect(formatAccountingAmountString('-0.004')).toBe('($ 0,004)')
  })

  it('still renders an exact zero as zero', () => {
    expect(formatAccountingAmountString('0.00')).toBe('$ 0,00')
  })
})

describe('isPlainObject / isArrayOfObjects', () => {
  it('detects a plain object but not an array', () => {
    expect(isPlainObject({ nombre: 'x' })).toBe(true)
    expect(isPlainObject([{ nombre: 'x' }])).toBe(false)
    expect(isPlainObject(null)).toBe(false)
  })

  it('detects a non-empty array whose items are all objects', () => {
    expect(isArrayOfObjects([{ valor: 1 }, { valor: 2 }])).toBe(true)
    expect(isArrayOfObjects([])).toBe(false)
    expect(isArrayOfObjects(['a', 'b'])).toBe(false)
  })
})

describe('formatScalarValue', () => {
  it('renders an em dash for empty values', () => {
    expect(formatScalarValue('valor', null)).toBe('—')
    expect(formatScalarValue('valor', undefined)).toBe('—')
  })

  it('formats currency-like keys with accounting number format', () => {
    expect(formatScalarValue('saldo_disponible', 1234567)).toBe('$ 1.234.567,00')
  })

  it('wraps a negative currency-like value in parentheses', () => {
    expect(formatScalarValue('valor', -512.5)).toBe('($ 512,50)')
  })

  it('stringifies non-currency values as-is', () => {
    expect(formatScalarValue('contribuyente', 'JULIAN')).toBe('JULIAN')
    expect(formatScalarValue('anio_gravable', 2024)).toBe('2024')
  })
})

describe('formatSampleAmount', () => {
  it('shows a figure the way the certificate beside it prints one', () => {
    // The whole point of showing the sample value is that it can be checked
    // against the paper at a glance, which `150464.81` cannot be.
    expect(formatSampleAmount('150464.81')).toBe('$ 150.464,81')
  })

  it('leaves a value that is already grouped exactly as it was read', () => {
    // `Number("150.464,81")` is NaN — forcing the format here would replace a
    // correct figure with "$ NaN".
    expect(formatSampleAmount('150.464,81')).toBe('150.464,81')
  })

  it('leaves anything that is not a number alone', () => {
    expect(formatSampleAmount('JULIAN ANDRES BUITRAGO')).toBe('JULIAN ANDRES BUITRAGO')
    expect(formatSampleAmount('')).toBe('')
  })

  it('reads a negative as accountants read one', () => {
    expect(formatSampleAmount('-1234.5')).toBe('($ 1.234,50)')
  })
})
