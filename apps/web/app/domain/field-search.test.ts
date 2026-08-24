import { describe, expect, it } from 'vitest'
import { matchesFieldQuery, queryTerms } from './field-search'

describe('queryTerms', () => {
  it('reads nothing out of blank input', () => {
    expect(queryTerms('   ')).toEqual([])
  })

  it('splits on whitespace and folds accents away', () => {
    expect(queryTerms('  Retención  Saldo ')).toEqual(['retencion', 'saldo'])
  })
})

describe('matchesFieldQuery', () => {
  const parts = [
    'Retención practicada rendimientos',
    'retenciones[].valor',
    '$ 19.586,00',
    'Retenciones año gravable'
  ]

  it('matches everything when nothing was typed', () => {
    expect(matchesFieldQuery('', ['saldo'])).toBe(true)
    expect(matchesFieldQuery('  ', [])).toBe(true)
  })

  it('finds a field by the words printed on the paper, accents aside', () => {
    expect(matchesFieldQuery('retencion', parts)).toBe(true)
    expect(matchesFieldQuery('RETENCIÓN', parts)).toBe(true)
  })

  it('finds a field by a fragment of the value read from the sample', () => {
    expect(matchesFieldQuery('586', parts)).toBe(true)
  })

  it('finds a field by its schema path', () => {
    expect(matchesFieldQuery('retenciones[].valor', parts)).toBe(true)
  })

  it('narrows with each further term instead of widening', () => {
    expect(matchesFieldQuery('retencion gravable', parts)).toBe(true)
    expect(matchesFieldQuery('retencion saldo', parts)).toBe(false)
  })

  it('ignores parts the screen has nothing to say about', () => {
    expect(matchesFieldQuery('saldo', ['Saldo', null, undefined])).toBe(true)
  })
})
