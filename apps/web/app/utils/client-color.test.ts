import { describe, expect, it } from 'vitest'
import { colorForClient } from '~/utils/client-color'

describe('colorForClient', () => {
  it('is deterministic for the same client id', () => {
    expect(colorForClient('client-42')).toEqual(colorForClient('client-42'))
  })

  it('distributes different ids across the palette', () => {
    const ids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    const colors = new Set(ids.map(id => colorForClient(id).bg))

    expect(colors.size).toBeGreaterThan(1)
  })

  it('always returns a bg/fg pair from the 6-tone palette', () => {
    const { bg, fg } = colorForClient('some-client-id')

    expect(bg).toMatch(/^bg-avatar-[1-6]-bg$/)
    expect(fg).toMatch(/^text-avatar-[1-6]-fg$/)
  })
})
