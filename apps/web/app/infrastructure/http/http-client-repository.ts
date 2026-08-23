import type { Client } from '~/domain/entities/client'
import type {
  ClientRepository,
  ImportSummary,
  RegisterClientInput
} from '~/application/ports/client-repository'

interface ClientDto {
  id: string
  name: string
  tax_id: string | null
  email: string | null
  created_at: string
  drive_folder_id: string | null
}

interface ImportDto {
  created: ClientDto[]
  renamed: ClientDto[]
  unchanged: number
}

function toClient(dto: ClientDto): Client {
  return {
    id: dto.id,
    name: dto.name,
    taxId: dto.tax_id,
    email: dto.email,
    createdAt: dto.created_at,
    driveFolderId: dto.drive_folder_id
  }
}

export class HttpClientRepository implements ClientRepository {
  constructor(private readonly baseUrl: string) {}

  async list(): Promise<Client[]> {
    // The server requires a session cookie on every business endpoint.
    const dtos = await $fetch<ClientDto[]>('/clients', {
      baseURL: this.baseUrl,
      credentials: 'include'
    })
    return dtos.map(toClient)
  }

  async register(input: RegisterClientInput): Promise<Client> {
    const dto = await $fetch<ClientDto>('/clients', {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST',
      body: { name: input.name, tax_id: input.taxId, email: input.email }
    })
    return toClient(dto)
  }

  async importFromDrive(): Promise<ImportSummary> {
    const dto = await $fetch<ImportDto>('/clients/import', {
      baseURL: this.baseUrl,
      credentials: 'include',
      method: 'POST'
    })
    return {
      created: dto.created.map(toClient),
      renamed: dto.renamed.map(toClient),
      unchanged: dto.unchanged
    }
  }
}
