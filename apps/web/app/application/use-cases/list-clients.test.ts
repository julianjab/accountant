import { describe, expect, it } from 'vitest'
import type { Client } from '~/domain/entities/client'
import type {
  ClientRepository,
  ImportSummary,
  RegisterClientInput
} from '~/application/ports/client-repository'
import { ListClients } from '~/application/use-cases/list-clients'

class FakeClientRepository implements ClientRepository {
  constructor(private readonly clients: Client[]) {}

  list(): Promise<Client[]> {
    return Promise.resolve(this.clients)
  }

  get(_id: string): Promise<Client | null> {
    throw new Error('not implemented')
  }

  register(_input: RegisterClientInput): Promise<Client> {
    throw new Error('not implemented')
  }

  importFromDrive(): Promise<ImportSummary> {
    throw new Error('not implemented')
  }
}

describe('ListClients', () => {
  it('returns the clients from the repository', async () => {
    const clients: Client[] = [
      {
        id: '1',
        name: 'Jane Doe',
        taxId: '123',
        email: null,
        createdAt: '2026-01-01',
        driveFolderId: null,
        driveFolderUrl: null,
        spreadsheetUrl: null
      }
    ]
    const useCase = new ListClients(new FakeClientRepository(clients))

    await expect(useCase.execute()).resolves.toEqual(clients)
  })
})
