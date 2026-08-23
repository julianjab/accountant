import type { ClientRepository, ImportSummary } from '~/application/ports/client-repository'

export class ImportClientsFromDrive {
  constructor(private readonly clients: ClientRepository) {}

  execute(): Promise<ImportSummary> {
    return this.clients.importFromDrive()
  }
}
