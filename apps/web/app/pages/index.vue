<script setup lang="ts">
import type { DocumentStatus } from '~/domain/entities/document'

const VALID_STATUSES: DocumentStatus[] = ['pending', 'classifying', 'running_ocr', 'processed', 'approved', 'failed']

const { t } = useI18n()
const route = useRoute()
const status = computed(() => {
  const value = route.query.status
  return VALID_STATUSES.includes(value as DocumentStatus) ? (value as DocumentStatus) : undefined
})
const useCase = useListInboxUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()
const showSignedOut = computed(() => !isAuthLoading.value && !isAuthenticated.value)

// "Procesados hoy" / "Tiempo medio" must use the preparer's local day (see acceptance
// criteria), not the SSR host's timezone — `new Date()` evaluated during SSR would use
// the server's TZ instead. Fetching client-only makes `now` always reflect the browser.
// Deferred on top of that: the endpoint needs the session cookie, which SSR does not
// carry, and fetching before sign-in would answer 401 and render as "inbox is empty" —
// a different statement entirely (see clients/index.vue).
const { data: inbox, error: inboxError, refresh: refreshInbox } = await useAsyncData(
  'inbox',
  () => useCase.execute({ status: status.value, now: new Date() }),
  { immediate: false, watch: [status], server: false }
)

watch(isAuthenticated, authenticated => authenticated && refreshInbox(), { immediate: true })

const totals = computed(() => inbox.value?.totals)
const groups = computed(() => inbox.value?.groups ?? [])
const totalDocuments = computed(() => inbox.value?.totalDocuments ?? 0)
const filteredDocuments = computed(() => inbox.value?.filteredDocuments ?? 0)
const documentTypesById = computed(() => inbox.value?.documentTypesById ?? {})

const emptyStateVariant = computed(() => {
  if (totalDocuments.value === 0) return 'empty'
  // groups.length, not filteredDocuments: a document whose client no longer exists is
  // dropped by ListInbox, so filteredDocuments can be > 0 with nothing left to render.
  if (groups.value.length === 0) return 'no-results'
  return null
})

function formatDuration(ms: number): string {
  const totalSeconds = Math.round(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return minutes === 0 ? `${seconds}s` : `${minutes}m ${seconds}s`
}

const avgProcessingLabel = computed(() => {
  const ms = totals.value?.avgProcessingMs
  return ms == null ? t('inbox.metrics.avgProcessingTimeEmpty') : formatDuration(ms)
})
</script>

<template>
  <UContainer class="max-w-[1180px] py-[30px]">
    <h1 class="text-[27px] font-bold tracking-[-0.02em] text-neutral-900">
      {{ t('inbox.title') }}
    </h1>

    <!--
      ClientOnly: the inbox data is fetched client-only (see the "now" comment above) so
      "today" always matches the browser's timezone. Without this wrapper, the first
      client render mismatches whatever (empty) state SSR produced and Vue logs a
      hydration warning.
    -->
    <ClientOnly>
      <p
        v-if="isAuthLoading"
        class="mt-[26px] text-muted"
      >
        {{ t('auth.loading') }}
      </p>

      <p
        v-else-if="showSignedOut"
        class="mt-[26px] text-muted"
      >
        {{ t('inbox.signInRequired') }}
      </p>

      <p
        v-else-if="inboxError"
        class="mt-[26px] text-error"
      >
        {{ t('inbox.loadError') }}
      </p>

      <template v-else>
        <div class="mt-[26px] grid grid-cols-4 gap-3">
          <InboxMetricCard
            :label="t('inbox.metrics.unprocessed')"
            :value="String(totals?.unprocessed ?? 0)"
          />
          <InboxMetricCard
            :label="t('inbox.metrics.processedToday')"
            :value="String(totals?.processedToday ?? 0)"
            variant="success"
          />
          <InboxMetricCard
            :label="t('inbox.metrics.failed')"
            :value="String(totals?.failed ?? 0)"
            variant="danger"
          />
          <InboxMetricCard
            :label="t('inbox.metrics.avgProcessingTime')"
            :value="avgProcessingLabel"
          />
        </div>

        <div class="mt-[26px] overflow-hidden rounded-xl border border-line-100 bg-white">
          <InboxStatusFilter
            :status="status"
            :total="totalDocuments"
            :filtered="filteredDocuments"
          />

          <InboxEmptyState
            v-if="emptyStateVariant"
            :variant="emptyStateVariant"
          />

          <InboxGroup
            v-for="group in groups"
            :key="group.client.id"
            :client="group.client"
            :count="group.documents.length"
          >
            <InboxDocumentRow
              v-for="document in group.documents"
              :key="document.id"
              :document="document"
              :document-type="document.documentTypeId ? documentTypesById[document.documentTypeId] : undefined"
            />
          </InboxGroup>
        </div>
      </template>
    </ClientOnly>
  </UContainer>
</template>
