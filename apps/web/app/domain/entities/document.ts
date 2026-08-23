export type DocumentStatus
  = | 'pending'
    | 'classifying'
    | 'running_ocr'
    | 'processed'
    | 'approved'
    | 'failed'

export interface ClientDocument {
  id: string
  clientId: string
  documentTypeId: string | null
  driveFileId: string
  fileName: string
  mimeType: string
  status: DocumentStatus
  error: string | null
  createdAt: string
}
