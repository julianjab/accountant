import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type {
  DefineDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { DefineDocumentType } from '~/application/use-cases/define-document-type'

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  receivedInput: DefineDocumentTypeInput | null = null

  constructor(private readonly documentType: DocumentType) {}

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  define(input: DefineDocumentTypeInput): Promise<DocumentType> {
    this.receivedInput = input
    return Promise.resolve(this.documentType)
  }

  update(_id: string, _changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    throw new Error('not implemented')
  }
}

describe('DefineDocumentType', () => {
  it('forwards the input to the repository and returns the created document type', async () => {
    const documentType: DocumentType = {
      id: '1',
      name: 'Bancolombia statement',
      description: 'Monthly bank statement',
      extractionPrompt: 'Extract the statement fields',
      extractionSchema: { properties: { balance: { type: 'number' } } },
      active: true,
      createdAt: '2026-01-01',
      fields: []
    }
    const repository = new FakeDocumentTypeRepository(documentType)
    const useCase = new DefineDocumentType(repository)
    const sampleFile = new File(['sample'], 'sample.pdf', { type: 'application/pdf' })
    const input: DefineDocumentTypeInput = {
      name: 'Bancolombia statement',
      description: 'Monthly bank statement',
      sampleFile
    }

    await expect(useCase.execute(input)).resolves.toEqual(documentType)
    expect(repository.receivedInput).toEqual(input)
  })
})
