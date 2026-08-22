import type { Client } from '~/domain/entities/client'
import type { ClientRepository } from '~/application/ports/client-repository'

export class ListClients {
  constructor(private readonly clients: ClientRepository) {}

  execute(): Promise<Client[]> {
    return this.clients.list()
  }
}
