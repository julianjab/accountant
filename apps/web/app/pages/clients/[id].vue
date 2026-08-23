<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'
import ClientHeader from '~/infrastructure/components/clients/ClientHeader.vue'
import ClientDocumentList from '~/infrastructure/components/clients/ClientDocumentList.vue'
import MonthlySummaryCard from '~/infrastructure/components/clients/MonthlySummaryCard.vue'
import ConfiguredTypesCard from '~/infrastructure/components/clients/ConfiguredTypesCard.vue'

const { t } = useI18n()
const route = useRoute()
const id = String(route.params.id)

const getClient = useGetClientUseCase()
const listClientDocuments = useListClientDocumentsUseCase()
const listActiveDocumentTypes = useListActiveDocumentTypesUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()

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

watch(
  isAuthenticated,
  (authenticated) => {
    if (!authenticated) return
    refreshClient()
    refreshDocuments()
    refreshTypes()
  },
  { immediate: true }
)

const tabItems = computed(() => [
  { label: t('clients.detail.tabs.documents'), slot: 'documents' as const },
  { label: t('clients.detail.tabs.extractedData'), slot: 'extractedData' as const },
  { label: t('clients.detail.tabs.spreadsheets'), slot: 'spreadsheets' as const }
])
</script>

<template>
  <UContainer class="py-8">
    <div
      v-if="isAuthLoading || clientPending"
      class="text-[13px] text-neutral-700"
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
      <h1 class="text-[20px] font-semibold text-neutral-900">
        {{ t('clients.detail.notFound.title') }}
      </h1>
      <p class="text-[13px] text-neutral-700">
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

      <div class="grid grid-cols-1 items-start gap-5 lg:grid-cols-[1fr_296px]">
        <UCard :ui="{ body: 'p-0 sm:p-0' }">
          <UTabs
            :items="tabItems"
            :ui="{
              list: 'border-b border-line-50 bg-transparent rounded-none p-0 gap-4 px-4',
              indicator: 'hidden',
              trigger: 'rounded-none border-b-2 border-transparent px-0 py-2.5 text-[13px] font-semibold text-neutral-600 data-[state=active]:border-green-600 data-[state=active]:text-neutral-900',
              content: 'p-0'
            }"
          >
            <template #documents>
              <ClientDocumentList
                :documents="documents ?? []"
                :types="types ?? []"
              />
            </template>
            <template #extractedData>
              <p class="p-4 text-[13px] text-neutral-700">
                {{ t('clients.detail.comingSoon') }}
              </p>
            </template>
            <template #spreadsheets>
              <p class="p-4 text-[13px] text-neutral-700">
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
