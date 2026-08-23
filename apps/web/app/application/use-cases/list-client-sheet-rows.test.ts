import { describe, expect, it } from 'vitest'
import type { SheetRow } from '~/domain/entities/sheet-row'
import type { SpreadsheetRepository } from '~/application/ports/spreadsheet-repository'
import { ListClientSheetRows } from '~/application/use-cases/list-client-sheet-rows'

class FakeSpreadsheetRepository implements SpreadsheetRepository {
  constructor(private readonly rowsByClient: Record<string, SheetRow[]>) {}

  listByClient(clientId: string): Promise<SheetRow[]> {
    return Promise.resolve(this.rowsByClient[clientId] ?? [])
  }
}

describe('ListClientSheetRows', () => {
  it('returns the rows for the given client', async () => {
    const rows: SheetRow[] = [
      {
        sourceDocumentId: 'doc-1',
        sourceDocumentFileName: 'doc.pdf',
        date: '2026-01-05',
        description: 'Pago',
        amount: '1000',
        tax: '190'
      }
    ]
    const useCase = new ListClientSheetRows(
      new FakeSpreadsheetRepository({ 'client-1': rows })
    )

    await expect(useCase.execute('client-1')).resolves.toEqual(rows)
  })

  it('returns an empty list for a client with no approved rows', async () => {
    const useCase = new ListClientSheetRows(new FakeSpreadsheetRepository({}))

    await expect(useCase.execute('client-1')).resolves.toEqual([])
  })
})
