import type { Client } from '~/domain/entities/client'

export interface RegisterClientInput {
  name: string
  taxId: string | null
  email: string | null
}

export interface ImportSummary {
  created: Client[]
  renamed: Client[]
  unchanged: number
}

export interface ClientRepository {
  list: () => Promise<Client[]>
  register: (input: RegisterClientInput) => Promise<Client>
  /** Mirrors the subfolders of the Drive clients folder into the client list. */
  importFromDrive: () => Promise<ImportSummary>
}
