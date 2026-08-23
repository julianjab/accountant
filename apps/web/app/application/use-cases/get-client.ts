import type { Client } from '~/domain/entities/client'
import type { ClientRepository } from '~/application/ports/client-repository'

export class GetClient {
  constructor(private readonly clients: ClientRepository) {}

  execute(id: string): Promise<Client | null> {
    return this.clients.get(id)
  }
}
