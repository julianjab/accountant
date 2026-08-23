import type { Client } from '~/domain/entities/client'
import type { ClientRepository, RegisterClientInput } from '~/application/ports/client-repository'

interface ClientDto {
  id: string
  name: string
  tax_id: string
  email: string | null
  created_at: string
  drive_folder_url: string | null
}

function toClient(dto: ClientDto): Client {
  return {
    id: dto.id,
    name: dto.name,
    taxId: dto.tax_id,
    email: dto.email,
    createdAt: dto.created_at,
    driveFolderUrl: dto.drive_folder_url
  }
}

function isNotFoundError(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'statusCode' in error
    && (error as { statusCode?: number }).statusCode === 404
}

export class HttpClientRepository implements ClientRepository {
  constructor(private readonly baseUrl: string) {}

  async list(): Promise<Client[]> {
    const dtos = await $fetch<ClientDto[]>('/clients', { baseURL: this.baseUrl })
    return dtos.map(toClient)
  }

  async get(id: string): Promise<Client | null> {
    try {
      const dto = await $fetch<ClientDto>(`/clients/${id}`, { baseURL: this.baseUrl })
      return toClient(dto)
    }
    catch (error) {
      if (isNotFoundError(error)) {
        return null
      }
      throw error
    }
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
