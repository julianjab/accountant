<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ReconciliationReport } from '~/domain/entities/reconciliation'
import ClientHeader from '~/infrastructure/components/clients/ClientHeader.vue'
import ClientDocumentList from '~/infrastructure/components/clients/ClientDocumentList.vue'
import MonthlySummaryCard from '~/infrastructure/components/clients/MonthlySummaryCard.vue'
import ConfiguredTypesCard from '~/infrastructure/components/clients/ConfiguredTypesCard.vue'
import SyncDriveButton from '~/infrastructure/components/clients/SyncDriveButton.vue'
import ReconciliationPanel from '~/infrastructure/components/reconciliation/ReconciliationPanel.vue'

const { t } = useI18n()
const route = useRoute()
const id = String(route.params.id)

const getClient = useGetClientUseCase()
const listClientDocuments = useListClientDocumentsUseCase()
const listActiveDocumentTypes = useListActiveDocumentTypesUseCase()
const getReconciliationReport = useGetReconciliationReportUseCase()

// One reconciliation model and one tax year for now.
const KIND_ID = 'exogena_dian'
const PERIOD = '2025'
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()
const { setLabel: setBreadcrumbLabel, clearLabel: clearBreadcrumbLabel } = useBreadcrumbLabels()

// Deferred and client-only on purpose: these endpoints need the session
// cookie, which SSR does not carry (see clients/index.vue).
const { data: client, pending: clientPending, refresh: refreshClient } = await useAsyncData<
  Client | null
>(`client:${id}`, () => getClient.execute(id), { immediate: false, server: false })
const { data: documents, refresh: refreshDocuments } = await useAsyncData<ClientDocument[]>(
  `documents:${id}`,
  () => listClientDocuments.execute(id),
  { immediate: false, server: false, default: () => [] }
)
const { data: types, refresh: refreshTypes } = await useAsyncData<DocumentType[]>(
  'document-types',
  () => listActiveDocumentTypes.execute(),
  { immediate: false, server: false, default: () => [] }
)

// Read here rather than only inside the reconciliation tab: the document list
// needs it too, to show which certificates the exogena is still waiting for.
const { data: report, refresh: refreshReport } = await useAsyncData<ReconciliationReport | null>(
  `reconciliation:${id}`,
  () => getReconciliationReport.execute(KIND_ID, id, PERIOD),
  { immediate: false, server: false, default: () => null }
)

watch(
  isAuthenticated,
  (authenticated) => {
    if (!authenticated) return
    refreshClient()
    refreshDocuments()
    refreshTypes()
    refreshReport()
  },
  { immediate: true }
)

// The breadcrumb only knows the URL (`/clients/<id>`); this is the one place that also has
// the client's name, so it hands it over rather than leaving the crumb as a raw id.
//
// Pinned at setup rather than read from `route` each time: `route` is the global reactive
// object, so by the time this page unmounts it already points at wherever we navigated to.
// Clearing that path would wipe the label the *next* page just set for itself, and leave
// this one's behind forever.
const ownPath = route.path

watch(
  client,
  (loadedClient) => {
    if (loadedClient) {
      setBreadcrumbLabel(ownPath, loadedClient.name)
    }
  },
  { immediate: true }
)

onUnmounted(() => clearBreadcrumbLabel(ownPath))

const tabItems = computed(() => [
  { label: t('clients.detail.tabs.documents'), slot: 'documents' as const },
  { label: t('clients.detail.tabs.reconciliation'), slot: 'reconciliation' as const },
  { label: t('clients.detail.tabs.spreadsheets'), slot: 'spreadsheets' as const }
])
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <div
      v-if="isAuthLoading || clientPending"
      class="text-[13px] text-toned"
    >
      {{ t('auth.loading') }}
    </div>

    <p
      v-else-if="!isAuthenticated"
      class="text-muted"
      data-testid="clients-signed-out"
    >
      {{ t('clients.signInRequired') }}
    </p>

    <div
      v-else-if="!client"
      class="flex flex-col items-start gap-3 py-8"
    >
      <h1 class="text-[18px] font-semibold text-highlighted sm:text-[20px]">
        {{ t('clients.detail.notFound.title') }}
      </h1>
      <p class="text-[13px] text-toned">
        {{ t('clients.detail.notFound.description') }}
      </p>
      <UButton
        :label="t('clients.detail.notFound.backToList')"
        icon="i-lucide-arrow-left"
        variant="outline"
        to="/clients"
      />
    </div>

    <template v-else>
      <ClientHeader :client="client" />

      <div class="grid grid-cols-1 items-start gap-4 sm:gap-5 lg:grid-cols-[1fr_296px]">
        <UCard :ui="{ body: 'p-0 sm:p-0' }">
          <UTabs
            :items="tabItems"
            :ui="{
              list: 'border-b border-default bg-transparent rounded-none p-0 gap-4 px-4 overflow-x-auto',
              indicator: 'hidden',
              trigger: 'shrink-0 rounded-none border-b-2 border-transparent px-0 py-2.5 text-[13px] font-semibold text-muted data-[state=active]:border-green-600 data-[state=active]:text-highlighted',
              content: 'p-0'
            }"
          >
            <template #documents>
              <div class="flex justify-end px-4 pt-3">
                <SyncDriveButton
                  :client-id="id"
                  @imported="refreshDocuments"
                />
              </div>
              <ClientDocumentList
                :documents="documents ?? []"
                :types="types ?? []"
                :report="report"
              />
            </template>
            <template #reconciliation>
              <ReconciliationPanel :client-id="id" />
            </template>
            <template #spreadsheets>
              <p class="p-4 text-[13px] text-toned">
                {{ t('clients.detail.comingSoon') }}
              </p>
            </template>
          </UTabs>
        </UCard>

        <div class="flex flex-col gap-3.5">
          <MonthlySummaryCard :documents="documents ?? []" />
          <ConfiguredTypesCard :types="types ?? []" />
        </div>
      </div>
    </template>
  </UContainer>
</template>
