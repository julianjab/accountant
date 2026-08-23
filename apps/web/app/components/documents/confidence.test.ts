import { describe, expect, it } from 'vitest'
import {
  confidenceBarColorClass,
  confidenceBarWidthPercent,
  confidenceLevel,
  confidenceValueColorClass
} from '~/components/documents/confidence'

describe('confidenceLevel', () => {
  it('is high above the 0.90 threshold', () => {
    expect(confidenceLevel(0.95)).toBe('high')
  })

  it('is low at or below the 0.90 threshold', () => {
    expect(confidenceLevel(0.9)).toBe('low')
    expect(confidenceLevel(0.5)).toBe('low')
  })
})

describe('confidenceValueColorClass', () => {
  it('is highlighted when confidence is null', () => {
    expect(confidenceValueColorClass(null)).toBe('text-highlighted')
  })

  it('is highlighted above the threshold and warning at or below it', () => {
    expect(confidenceValueColorClass(0.95)).toBe('text-highlighted')
    expect(confidenceValueColorClass(0.9)).toBe('text-warning')
  })
})

describe('confidenceBarColorClass', () => {
  it('is success above the threshold and warning at or below it', () => {
    expect(confidenceBarColorClass(0.95)).toBe('bg-success')
    expect(confidenceBarColorClass(0.9)).toBe('bg-warning')
  })
})

describe('confidenceBarWidthPercent', () => {
  it('rounds the confidence to a percentage', () => {
    expect(confidenceBarWidthPercent(0.876)).toBe(88)
    expect(confidenceBarWidthPercent(1)).toBe(100)
  })
})
