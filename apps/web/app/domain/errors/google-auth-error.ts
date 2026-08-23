export type GoogleAuthErrorCode = 'missingClientId' | 'popupClosed' | 'driveDenied'

export class GoogleAuthError extends Error {
  constructor(public readonly code: GoogleAuthErrorCode) {
    super(code)
    this.name = 'GoogleAuthError'
  }
}
