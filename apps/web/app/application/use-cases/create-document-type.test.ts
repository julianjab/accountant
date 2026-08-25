import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeCreation, DocumentTypeUpdate, DocumentTypeField } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  DocumentTypeRepository,
  ProposeDocumentTypeInput,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { CreateDocumentType } from '~/application/use-cases/create-document-type'

const CREATED: DocumentTypeCreation = {
  documentType: {
    id: 'dt-1',
    name: 'Certificado GMF',
    description: 'Certificado de GMF',
    extractionPrompt: 'Extraelo',
    extractionSchema: { type: 'object', properties: {} },
    candidateSchema: null,
    active: true,
    createdAt: '2026-08-24',
    fields: [{ path: 'gmf', label: 'Valor GMF', role: 'amount', section: 'GMF', sampleValue: '' }],
    taxYears: [],
    sampleDocumentId: null
  },
  unmappedFields: []
}

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  receivedInput: CreateDocumentTypeInput | null = null

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  describeFields(): Promise<DocumentTypeField[]> {
    throw new Error('not implemented')
  }

  propose(_input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    throw new Error('not implemented')
  }

  create(input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    this.receivedInput = input
    return Promise.resolve(CREATED)
  }

  remove(_id: string): Promise<void> {
    return Promise.resolve()
  }

  update(_id: string, _changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    throw new Error('not implemented')
  }
}

describe('CreateDocumentType', () => {
  it('forwards the approved configuration and returns the type with its mapping changes', async () => {
    const repository = new FakeDocumentTypeRepository()
    const input: CreateDocumentTypeInput = {
      name: 'Certificado GMF',
      description: 'Certificado de GMF',
      extractionPrompt: 'Extraelo',
      extractionSchema: { type: 'object', properties: {} },
      candidateSchema: null,
      fieldMappings: [{ fieldPath: 'gmf', conceptId: 'bank:gmf', accountPath: null, sign: -1 }],
      fields: [{ path: 'gmf', label: 'Valor GMF', role: 'amount', section: 'GMF', sampleValue: '' }],
      reporterPath: 'nit',
      reporterTaxId: null,
      reporterName: null,
      period: null,
      reporterNamePath: null,
      periodPath: 'anio',
      taxYears: [],
      kindId: 'exogena_dian',
      sampleDocumentId: 'doc-1'
    }

    await expect(new CreateDocumentType(repository).execute(input)).resolves.toEqual(CREATED)
    expect(repository.receivedInput).toEqual(input)
  })
})
