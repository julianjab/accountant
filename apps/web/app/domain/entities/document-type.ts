export interface DocumentType {
  id: string
  name: string
  description: string
  extractionPrompt: string
  extractionSchema: Record<string, unknown>
  active: boolean
  createdAt: string
}
