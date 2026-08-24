import { describe, expect, it } from 'vitest'
import { changesNothing, compareSchemaPaths } from './schema-revision'

describe('compareSchemaPaths', () => {
  it('reports what a regeneration would add, drop and keep', () => {
    const revision = compareSchemaPaths(
      ['obligaciones[].capital', 'obligaciones[].interes', 'pie_de_pagina'],
      ['obligaciones[].concepto', 'obligaciones[].capital', 'obligaciones[].interes']
    )

    expect(revision.added).toEqual(['obligaciones[].concepto'])
    expect(revision.removed).toEqual(['pie_de_pagina'])
    expect(revision.kept).toEqual(['obligaciones[].capital', 'obligaciones[].interes'])
  })

  it('keeps the current order, which is the order the screen lists fields in', () => {
    const revision = compareSchemaPaths(['b', 'a'], ['a', 'b'])

    expect(revision.kept).toEqual(['b', 'a'])
    expect(changesNothing(revision)).toBe(true)
  })

  it('reads a revision that only adds as adding', () => {
    const revision = compareSchemaPaths(['a'], ['a', 'b'])

    expect(revision.removed).toEqual([])
    expect(changesNothing(revision)).toBe(false)
  })
})
