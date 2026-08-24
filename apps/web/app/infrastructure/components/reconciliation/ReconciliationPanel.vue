<script setup lang="ts">
import type { FindingStatus, ReconciliationReport } from '~/domain/entities/reconciliation'

const props = defineProps<{ clientId: string }>()

const { t } = useI18n()
const getReport = useGetReconciliationReportUseCase()
const runReconciliation = useRunReconciliationUseCase()

// One reconciliation model and one tax year for now, so neither is a choice
// the screen has to offer.
const KIND_ID = 'exogena_dian'
const PERIOD = '2025'

const running = ref(false)
const error = ref<string | null>(null)

const { data: report, refresh } = await useAsyncData<ReconciliationReport | null>(
  `reconciliation:${props.clientId}`,
  () => getReport.execute(KIND_ID, props.clientId, PERIOD),
  { server: false, default: () => null }
)

async function run() {
  running.value = true
  error.value = null
  try {
    report.value = await runReconciliation.execute(KIND_ID, props.clientId, PERIOD)
  } catch {
    error.value = t('reconciliation.runFailed')
    await refresh()
  } finally {
    running.value = false
  }
}

/** The exogena is the base being validated, so a row of this table is a row of
 * the exogena: who reported it, what they called it, and what they said it was
 * worth — then whatever the certificates turned out to say. Findings with no
 * spine facts are not exogena rows and are listed separately below. */
const rows = computed(() =>
  (report.value?.findings ?? [])
    .filter(finding => finding.spineFacts.length > 0)
    .map(finding => ({
      id: finding.id,
      status: finding.status,
      reporterName: finding.reporterName,
      // Verbatim from the exogena. One finding can cover several of its rows
      // (two account balances against one certified total), and each keeps its
      // own wording rather than being collapsed into the rule's label.
      details: finding.spineFacts.map(fact => ({
        text: fact.detail || finding.label,
        amount: fact.amount,
        account: fact.account,
        locator: fact.locator
      })),
      spineAmount: finding.spineAmount,
      evidenceAmount: finding.evidenceAmount,
      delta: finding.delta,
      hasEvidence: finding.evidenceFacts.length > 0,
      // Where the certified figure was read, so the row can link back to it.
      evidenceDocumentId: finding.evidenceFacts[0]?.sourceId ?? null,
      note: finding.note
    }))
)

/** Certified figures the exogena never mentions — often a deduction nobody
 * claimed, which is why they are shown rather than dropped. */
const unsupported = computed(() =>
  (report.value?.findings ?? []).filter(
    finding => finding.status === 'unsupported_by_spine' && finding.spineFacts.length === 0
  )
)

const ROW_TONE: Record<FindingStatus, string> = {
  matched: 'bg-green-50/70 dark:bg-green-950/30',
  matched_within_tolerance: 'bg-green-50/70 dark:bg-green-950/30',
  mismatch: 'bg-amber-50 dark:bg-amber-950/40',
  missing_evidence: 'bg-transparent',
  unsupported_by_spine: 'bg-transparent',
  out_of_scope: 'bg-transparent'
}

const MARK_TONE: Record<FindingStatus, string> = {
  matched: 'bg-green-600',
  matched_within_tolerance: 'bg-green-600',
  mismatch: 'bg-amber-500',
  missing_evidence: 'bg-neutral-300 dark:bg-neutral-700',
  unsupported_by_spine: 'bg-blue-400',
  out_of_scope: 'bg-neutral-200 dark:bg-neutral-800'
}
</script>

<template>
  <div class="p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-[13px] font-semibold text-highlighted">
          {{ t('reconciliation.title', { period: PERIOD }) }}
        </h3>
        <p
          v-if="report"
          class="text-[12px] text-muted"
        >
          {{ t('reconciliation.summary', {
            total: report.summary.totalFindings,
            reconciled: report.summary.reconciled,
            attention: report.summary.needingAttention
          }) }}
        </p>
      </div>
      <UButton
        :label="report ? t('reconciliation.rerun') : t('reconciliation.run')"
        icon="i-lucide-scale"
        size="sm"
        variant="outline"
        :loading="running"
        data-testid="reconciliation-run"
        @click="run"
      />
    </div>

    <p
      v-if="error"
      class="mt-3 text-[13px] text-red-600"
      data-testid="reconciliation-error"
    >
      {{ error }}
    </p>

    <p
      v-if="!report"
      class="mt-4 text-[13px] text-toned"
      data-testid="reconciliation-empty"
    >
      {{ t('reconciliation.notRunYet') }}
    </p>

    <template v-else>
      <!-- Scrolls inside itself: five columns of figures must not make the
           page scroll sideways on a phone. -->
      <div class="mt-4 overflow-x-auto">
        <table class="w-full min-w-[720px] border-collapse text-[12px]">
          <thead>
            <tr class="border-b border-default text-left text-[11px] uppercase text-muted">
              <th class="w-1.5" />
              <th class="py-2 pr-3 font-medium">
                {{ t('reconciliation.columns.reporter') }}
              </th>
              <th class="py-2 pr-3 font-medium">
                {{ t('reconciliation.columns.detail') }}
              </th>
              <th class="py-2 pr-3 text-right font-medium">
                {{ t('reconciliation.columns.exogenaAmount') }}
              </th>
              <th class="py-2 pr-3 text-right font-medium">
                {{ t('reconciliation.columns.certificateAmount') }}
              </th>
              <th class="py-2 text-right font-medium">
                {{ t('reconciliation.columns.difference') }}
              </th>
            </tr>
          </thead>
          <tbody data-testid="reconciliation-rows">
            <tr
              v-for="row in rows"
              :key="row.id"
              class="border-b border-default/60 align-top"
              :class="ROW_TONE[row.status]"
              :data-status="row.status"
            >
              <td class="py-2">
                <span
                  class="block h-full min-h-[1.5rem] w-1 rounded-sm"
                  :class="MARK_TONE[row.status]"
                  :title="t(`reconciliation.status.${row.status}`)"
                />
              </td>
              <td class="py-2 pr-3 text-toned">
                {{ row.reporterName }}
              </td>
              <td class="py-2 pr-3">
                <p
                  v-for="detail in row.details"
                  :key="`${row.id}-${detail.locator}`"
                  class="text-highlighted"
                >
                  {{ detail.text }}
                  <span
                    v-if="detail.account"
                    class="text-muted"
                  >· {{ detail.account }}</span>
                </p>
                <p
                  v-if="row.note"
                  class="text-[11px] text-muted"
                >
                  {{ row.note }}
                </p>
              </td>
              <td class="py-2 pr-3 text-right font-mono tabular-nums text-highlighted">
                <p
                  v-for="detail in row.details"
                  :key="`${row.id}-amount-${detail.locator}`"
                >
                  {{ detail.amount }}
                </p>
                <p
                  v-if="row.details.length > 1"
                  class="border-t border-default pt-0.5 font-semibold"
                >
                  {{ row.spineAmount }}
                </p>
              </td>
              <td class="py-2 pr-3 text-right font-mono tabular-nums">
                <NuxtLink
                  v-if="row.hasEvidence && row.evidenceDocumentId"
                  :to="`/documents/${row.evidenceDocumentId}`"
                  class="text-highlighted underline decoration-dotted underline-offset-2"
                >{{ row.evidenceAmount }}</NuxtLink>
                <span
                  v-else-if="row.hasEvidence"
                  class="text-highlighted"
                >{{ row.evidenceAmount }}</span>
                <span
                  v-else
                  class="text-muted"
                  data-testid="reconciliation-missing"
                >{{ t('reconciliation.columns.notFound') }}</span>
              </td>
              <td class="py-2 text-right font-mono tabular-nums text-toned">
                {{ row.hasEvidence ? row.delta : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <section
        v-if="unsupported.length > 0"
        class="mt-6"
      >
        <h4 class="text-[12px] font-semibold text-highlighted">
          {{ t('reconciliation.unsupportedTitle') }}
        </h4>
        <p class="mb-2 text-[11px] text-muted">
          {{ t('reconciliation.unsupportedHint') }}
        </p>
        <ul class="flex flex-col divide-y divide-default rounded border border-default">
          <li
            v-for="finding in unsupported"
            :key="finding.id"
            class="flex items-baseline justify-between gap-3 px-3 py-1.5"
          >
            <span class="text-[12px] text-toned">
              {{ finding.reporterName }} · {{ finding.label }}
            </span>
            <NuxtLink
              v-if="finding.evidenceFacts[0]"
              :to="`/documents/${finding.evidenceFacts[0].sourceId}`"
              class="shrink-0 font-mono text-[12px] tabular-nums text-highlighted underline decoration-dotted underline-offset-2"
            >{{ finding.evidenceAmount }}</NuxtLink>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
