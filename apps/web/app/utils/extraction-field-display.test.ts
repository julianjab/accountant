import { describe, expect, it } from 'vitest'
import {
  formatGroupedNumber,
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

describe('formatGroupedNumber', () => {
  it('groups thousands for the es-CO locale', () => {
    expect(formatGroupedNumber(9946131)).toBe('9.946.131')
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

  it('groups thousands for currency-like keys', () => {
    expect(formatScalarValue('saldo_disponible', 1234567)).toBe('1.234.567')
  })

  it('stringifies non-currency values as-is', () => {
    expect(formatScalarValue('contribuyente', 'JULIAN')).toBe('JULIAN')
    expect(formatScalarValue('anio_gravable', 2024)).toBe('2024')
  })
})
