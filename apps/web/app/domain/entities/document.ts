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
  processedAt: string | null
  /** Set when the file was read by a dedicated parser instead of OCR, which is
   * why such a document has no `documentTypeId`. Without it, a document read
   * this way is indistinguishable from one nothing could be made of. */
  sourceId: string | null
}
