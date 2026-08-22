import type { Client } from '~/domain/entities/client'
import type { ClientRepository, RegisterClientInput } from '~/application/ports/client-repository'

interface ClientDto {
  id: string
  name: string
  tax_id: string
  email: string | null
  created_at: string
}

function toClient(dto: ClientDto): Client {
  return {
    id: dto.id,
    name: dto.name,
    taxId: dto.tax_id,
    email: dto.email,
    createdAt: dto.created_at
  }
}

export class HttpClientRepository implements ClientRepository {
  constructor(private readonly baseUrl: string) {}

  async list(): Promise<Client[]> {
    const dtos = await $fetch<ClientDto[]>('/clients', { baseURL: this.baseUrl })
    return dtos.map(toClient)
  }

  async register(input: RegisterClientInput): Promise<Client> {
    const dto = await $fetch<ClientDto>('/clients', {
      baseURL: this.baseUrl,
      method: 'POST',
      body: { name: input.name, tax_id: input.taxId, email: input.email }
    })
    return toClient(dto)
  }
}
