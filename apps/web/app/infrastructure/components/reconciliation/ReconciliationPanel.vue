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

/** Tints the whole row rather than a badge: a spreadsheet is read by scanning
 * down a column, so the state has to survive peripheral vision. */
const ROW_TONE: Record<FindingStatus, string> = {
  matched: 'bg-green-50 dark:bg-green-950/40',
  matched_within_tolerance: 'bg-green-50 dark:bg-green-950/40',
  mismatch: 'bg-amber-50 dark:bg-amber-950/50',
  missing_evidence: '',
  unsupported_by_spine: '',
  out_of_scope: 'opacity-60'
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
      <!--
        Ruled like a sheet on purpose: this is a ledger being checked line by
        line, and the cell borders are what let the eye track a row across five
        columns. Scrolls inside itself so the page never scrolls sideways on a
        phone, and the header sticks so the columns stay named while scrolling.
      -->
      <div class="mt-4 max-h-[70vh] overflow-auto rounded border border-default">
        <table class="w-full min-w-[760px] border-collapse font-mono text-[12px]">
          <thead class="sticky top-0 z-10">
            <tr class="bg-elevated text-left text-[11px] uppercase tracking-wide text-muted">
              <th class="border-b border-r border-default px-2 py-1.5 font-medium">
                {{ t('reconciliation.columns.reporter') }}
              </th>
              <th class="border-b border-r border-default px-2 py-1.5 font-medium">
                {{ t('reconciliation.columns.detail') }}
              </th>
              <th class="border-b border-r border-default px-2 py-1.5 text-right font-medium">
                {{ t('reconciliation.columns.exogenaAmount') }}
              </th>
              <th class="border-b border-r border-default px-2 py-1.5 text-right font-medium">
                {{ t('reconciliation.columns.certificateAmount') }}
              </th>
              <th class="border-b border-default px-2 py-1.5 text-right font-medium">
                {{ t('reconciliation.columns.difference') }}
              </th>
            </tr>
          </thead>
          <tbody data-testid="reconciliation-rows">
            <template
              v-for="row in rows"
              :key="row.id"
            >
              <!--
                One line of the exogena is one line here. A rule covering
                several of them keeps each on its own row and adds a total
                beneath, because the accountant is reading their client's
                report and not our rule pack.
              -->
              <tr
                v-for="(detail, index) in row.details"
                :key="`${row.id}-${index}`"
                :class="ROW_TONE[row.status]"
                :data-status="row.status"
              >
                <td class="border-b border-r border-default px-2 py-1 align-top text-toned">
                  <span v-if="index === 0">{{ row.reporterName }}</span>
                </td>
                <td class="border-b border-r border-default px-2 py-1 align-top text-highlighted">
                  {{ detail.text }}
                  <span
                    v-if="detail.account"
                    class="text-muted"
                  >· {{ detail.account }}</span>
                  <!-- Why the row landed where it did — that the accounts were
                       paired on a partial identifier, that the certificate
                       splits into components what the exogena states as one
                       figure. Without it a mismatch is a number with no story. -->
                  <p
                    v-if="index === 0 && row.note"
                    class="mt-0.5 text-[11px] font-sans italic text-muted"
                    data-testid="finding-note"
                  >
                    {{ row.note }}
                  </p>
                </td>
                <td
                  class="border-b border-r border-default px-2 py-1 text-right align-top tabular-nums text-highlighted"
                >
                  {{ detail.amount }}
                </td>
                <td
                  class="border-b border-r border-default px-2 py-1 text-right align-top tabular-nums"
                >
                  <template v-if="index === 0 && row.details.length === 1">
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
                  </template>
                </td>
                <td class="border-b border-default px-2 py-1 text-right align-top tabular-nums text-toned">
                  <span v-if="index === 0 && row.details.length === 1">
                    {{ row.hasEvidence ? row.delta : '—' }}
                  </span>
                </td>
              </tr>

              <tr
                v-if="row.details.length > 1"
                :key="`${row.id}-total`"
                :class="ROW_TONE[row.status]"
                class="font-semibold"
              >
                <td class="border-b border-r border-default px-2 py-1" />
                <td class="border-b border-r border-default px-2 py-1 text-muted">
                  {{ t('reconciliation.total') }}
                </td>
                <td
                  class="border-b border-r border-default px-2 py-1 text-right tabular-nums text-highlighted"
                >
                  {{ row.spineAmount }}
                </td>
                <td class="border-b border-r border-default px-2 py-1 text-right tabular-nums">
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
                  >{{ t('reconciliation.columns.notFound') }}</span>
                </td>
                <td class="border-b border-default px-2 py-1 text-right tabular-nums text-toned">
                  {{ row.hasEvidence ? row.delta : '—' }}
                </td>
              </tr>
            </template>
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
        <div class="overflow-x-auto rounded border border-default">
          <table class="w-full min-w-[480px] border-collapse font-mono text-[12px]">
            <tbody>
              <tr
                v-for="finding in unsupported"
                :key="finding.id"
              >
                <td class="border-b border-r border-default px-2 py-1 text-toned">
                  {{ finding.reporterName }}
                </td>
                <td class="border-b border-r border-default px-2 py-1 text-highlighted">
                  {{ finding.label }}
                </td>
                <td class="border-b border-default px-2 py-1 text-right tabular-nums">
                  <NuxtLink
                    v-if="finding.evidenceFacts[0]"
                    :to="`/documents/${finding.evidenceFacts[0].sourceId}`"
                    class="text-highlighted underline decoration-dotted underline-offset-2"
                  >{{ finding.evidenceAmount }}</NuxtLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>
