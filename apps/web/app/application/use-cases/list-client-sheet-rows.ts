import type { SheetRow } from '~/domain/entities/sheet-row'
import type { SpreadsheetRepository } from '~/application/ports/spreadsheet-repository'

export class ListClientSheetRows {
  constructor(private readonly spreadsheets: SpreadsheetRepository) {}

  execute(clientId: string): Promise<SheetRow[]> {
    return this.spreadsheets.listByClient(clientId)
  }
}
