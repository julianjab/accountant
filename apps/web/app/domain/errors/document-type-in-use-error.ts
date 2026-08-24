/**
 * Refused because documents were already classified as this type.
 *
 * Its own error because the answer is not "try again": the accountant wanted
 * the type gone, and what they can actually do — deactivate it, so it stops
 * classifying while the documents filed under it stay readable — is a
 * different action, offered only when this is what happened.
 */
export class DocumentTypeInUseError extends Error {
  constructor(readonly detail: string) {
    super(detail)
    this.name = 'DocumentTypeInUseError'
  }
}
