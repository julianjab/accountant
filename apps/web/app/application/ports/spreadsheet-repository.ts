import type { SheetRow } from '~/domain/entities/sheet-row'

export interface SpreadsheetRepository {
  listByClient: (clientId: string) => Promise<SheetRow[]>
}
