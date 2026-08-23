export interface ExtractedData {
  id: string
  documentId: string
  fields: Record<string, unknown>
  confidence: number | null
  createdAt: string
}
