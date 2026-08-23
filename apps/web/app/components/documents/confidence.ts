const CONFIDENCE_THRESHOLD = 0.9

export type ConfidenceLevel = 'high' | 'low'

export function confidenceLevel(confidence: number): ConfidenceLevel {
  return confidence > CONFIDENCE_THRESHOLD ? 'high' : 'low'
}

export function confidenceValueColorClass(confidence: number | null): string {
  if (confidence === null) {
    return 'text-highlighted'
  }
  return confidenceLevel(confidence) === 'high' ? 'text-highlighted' : 'text-warning'
}

export function confidenceBarColorClass(confidence: number): string {
  return confidenceLevel(confidence) === 'high' ? 'bg-success' : 'bg-warning'
}

export function confidenceBarWidthPercent(confidence: number): number {
  return Math.round(confidence * 100)
}
