import { describe, expect, it, vi } from 'vitest'
import { ImportClientsFromDrive } from './import-clients-from-drive'
import type { ClientRepository } from '~/application/ports/client-repository'

describe('ImportClientsFromDrive', () => {
  it('returns the summary the repository reports', async () => {
    const summary = { created: [], renamed: [], unchanged: 3 }
    const clients: ClientRepository = {
      list: vi.fn(),
      get: vi.fn(),
      register: vi.fn(),
      importFromDrive: vi.fn().mockResolvedValue(summary)
    }

    await expect(new ImportClientsFromDrive(clients).execute()).resolves.toEqual(summary)
  })
})
