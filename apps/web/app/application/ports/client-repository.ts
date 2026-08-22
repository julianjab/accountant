import type { Client } from '~/domain/entities/client'

export interface RegisterClientInput {
  name: string
  taxId: string
  email: string | null
}

export interface ClientRepository {
  list: () => Promise<Client[]>
  register: (input: RegisterClientInput) => Promise<Client>
}
