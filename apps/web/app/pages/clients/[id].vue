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

const { data: client, pending: clientPending } = await useAsyncData<Client | null>(
  `client:${id}`,
  () => getClient.execute(id)
)
const { data: documents } = await useAsyncData<ClientDocument[]>(
  `documents:${id}`,
  () => listClientDocuments.execute(id)
)
const { data: types } = await useAsyncData<DocumentType[]>('document-types', () =>
  listActiveDocumentTypes.execute()
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
      v-if="clientPending"
      class="text-[13px] text-neutral-700"
    >
      {{ t('clients.detail.notFound.title') }}
    </div>

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
          <UTabs :items="tabItems">
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
