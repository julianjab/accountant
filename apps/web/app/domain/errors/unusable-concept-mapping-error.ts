/**
 * A mapping that could never produce a fact.
 *
 * Raised instead of saving, because the failure is otherwise invisible: the
 * server stores such a mapping happily, the type then looks configured, and
 * every claim comes back as missing evidence with nothing pointing at the
 * cause.
 */
export class UnusableConceptMappingError extends Error {
  constructor(public readonly reason: 'missingReporterPath') {
    super(reason)
    this.name = 'UnusableConceptMappingError'
  }
}
