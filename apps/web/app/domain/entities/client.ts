export interface Client {
  id: string
  name: string
  taxId: string | null
  email: string | null
  createdAt: string
  driveFolderId: string | null
  driveFolderUrl: string | null
}
