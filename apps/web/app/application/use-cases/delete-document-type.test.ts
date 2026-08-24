import { describe, expect, it, vi } from 'vitest'
import { DeleteDocumentType } from '~/application/use-cases/delete-document-type'
import { DocumentTypeInUseError } from '~/domain/errors/document-type-in-use-error'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'

function repository(remove: DocumentTypeRepository['remove']): DocumentTypeRepository {
  return {
    listActive: () => Promise.resolve([]),
    list: () => Promise.resolve([]),
    get: () => Promise.resolve(null),
    propose: () => Promise.reject(new Error('not used')),
    create: () => Promise.reject(new Error('not used')),
    update: () => Promise.reject(new Error('not used')),
    remove
  } as unknown as DocumentTypeRepository
}

describe('DeleteDocumentType', () => {
  it('asks the repository to remove exactly the type it was given', () => {
    const remove = vi.fn(() => Promise.resolve())

    new DeleteDocumentType(repository(remove)).execute('type-1')

    expect(remove).toHaveBeenCalledWith('type-1')
  })

  it('lets the refusal through, because it is not a failure to retry', async () => {
    // Documents are filed under the type. What the accountant can do about it
    // is deactivate it, which is a different action the screen only offers
    // when this is what came back.
    const remove = () => Promise.reject(new DocumentTypeInUseError('3 document(s)'))

    await expect(new DeleteDocumentType(repository(remove)).execute('type-1')).rejects.toThrow(
      DocumentTypeInUseError
    )
  })
})
