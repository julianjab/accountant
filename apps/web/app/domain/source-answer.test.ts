import { describe, expect, it } from 'vitest'
import { readSource, writeSource } from '~/domain/document-type-configuration'

const PATHS = ['issuer_nit', 'saldos.cuenta_ahorros']

describe('readSource', () => {
  it('reads a known path as the field to take the value from', () => {
    expect(readSource('issuer_nit', PATHS)).toEqual({ path: 'issuer_nit', value: null })
  })

  it('reads anything else as a value the user is declaring', () => {
    expect(readSource('890903938', PATHS)).toEqual({ path: null, value: '890903938' })
  })

  it('prefers the field over the literal text when both readings exist', () => {
    // Someone typing `issuer_nit` means the field. Read as a value it would
    // attribute every document of this type to a party called "issuer_nit".
    expect(readSource('issuer_nit', PATHS).path).toBe('issuer_nit')
  })

  it('treats an emptied box as no answer at all, not as an empty value', () => {
    expect(readSource('   ', PATHS)).toEqual({ path: null, value: null })
    expect(readSource(null, PATHS)).toEqual({ path: null, value: null })
  })

  it('trims, so a stray space does not turn a path into a declared value', () => {
    expect(readSource(' issuer_nit ', PATHS).path).toBe('issuer_nit')
  })
})

describe('writeSource', () => {
  it('shows the path when one is set', () => {
    expect(writeSource('issuer_nit', null)).toBe('issuer_nit')
  })

  it('shows the declared value when there is no path', () => {
    expect(writeSource(null, '890903938')).toBe('890903938')
  })

  it('is empty when neither is set', () => {
    expect(writeSource(null, null)).toBe('')
  })
})

describe('the sentinel that means "no field"', () => {
  it('is a declared value, not a path, if it ever reaches this', () => {
    // Belt to the braces: the suggestion lists exclude it, but read as a path
    // it would store one nothing can resolve, and the reporting party would
    // count as answered while attributing the figures to nobody.
    expect(readSource('__unset__', PATHS)).toEqual({ path: null, value: '__unset__' })
  })
})
