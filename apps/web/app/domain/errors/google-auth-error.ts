export type GoogleAuthErrorCode
  = | 'sessionUnavailable'
    | 'denied'
    | 'not_allowed'
    | 'drive_denied'
    | 'state'
    | 'no_refresh'
    | 'exchange'
    | 'server'

export class GoogleAuthError extends Error {
  constructor(public readonly code: GoogleAuthErrorCode) {
    super(code)
    this.name = 'GoogleAuthError'
  }
}
