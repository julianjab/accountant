import type { SheetRow } from '~/domain/entities/sheet-row'
import type { SpreadsheetRepository } from '~/application/ports/spreadsheet-repository'

interface SheetRowDto {
  source_document_id: string
  source_document_file_name: string
  date: string
  description: string
  amount: string
  tax: string
}

function toSheetRow(dto: SheetRowDto): SheetRow {
  return {
    sourceDocumentId: dto.source_document_id,
    sourceDocumentFileName: dto.source_document_file_name,
    date: dto.date,
    description: dto.description,
    amount: dto.amount,
    tax: dto.tax
  }
}

export class HttpSpreadsheetRepository implements SpreadsheetRepository {
  constructor(private readonly baseUrl: string) {}

  async listByClient(clientId: string): Promise<SheetRow[]> {
    const dtos = await $fetch<SheetRowDto[]>(`/clients/${clientId}/spreadsheet-rows`, {
      baseURL: this.baseUrl
    })
    return dtos.map(toSheetRow)
  }
}
