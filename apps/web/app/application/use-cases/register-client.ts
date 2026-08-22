import type { Client } from '~/domain/entities/client'
import type { ClientRepository, RegisterClientInput } from '~/application/ports/client-repository'

export class RegisterClient {
  constructor(private readonly clients: ClientRepository) {}

  execute(input: RegisterClientInput): Promise<Client> {
    return this.clients.register(input)
  }
}
