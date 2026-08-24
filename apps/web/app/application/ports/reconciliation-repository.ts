import type { ReconciliationReport } from '~/domain/entities/reconciliation'

export interface ReconciliationRepository {
  /** The last report computed for a client and period, or null if none has
   * been run — which is itself the answer the screen needs. */
  getReport: (
    kindId: string,
    clientId: string,
    period: string
  ) => Promise<ReconciliationReport | null>
  run: (kindId: string, clientId: string, period: string) => Promise<ReconciliationReport>
}
