import { describe, expect, it } from 'vitest'
import type { Client } from '~/domain/entities/client'
import type {
  ClientRepository,
  ImportSummary,
  RegisterClientInput
} from '~/application/ports/client-repository'
import { GetClient } from '~/application/use-cases/get-client'

class FakeClientRepository implements ClientRepository {
  constructor(private readonly clients: Client[]) {}

  list(): Promise<Client[]> {
    return Promise.resolve(this.clients)
  }

  get(id: string): Promise<Client | null> {
    return Promise.resolve(this.clients.find(c => c.id === id) ?? null)
  }

  register(_input: RegisterClientInput): Promise<Client> {
    throw new Error('not implemented')
  }

  importFromDrive(): Promise<ImportSummary> {
    throw new Error('not implemented')
  }
}

describe('GetClient', () => {
  it('returns the client from the repository', async () => {
    const client: Client = {
      id: '1',
      name: 'Jane Doe',
      taxId: '123',
      email: null,
      createdAt: '2026-01-01',
      driveFolderId: null,
      driveFolderUrl: null
    }
    const useCase = new GetClient(new FakeClientRepository([client]))

    await expect(useCase.execute('1')).resolves.toEqual(client)
  })

  it('returns null when the client does not exist', async () => {
    const useCase = new GetClient(new FakeClientRepository([]))

    await expect(useCase.execute('missing')).resolves.toBeNull()
  })
})
