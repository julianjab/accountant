<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import type { SheetRow } from '~/domain/entities/sheet-row'

const { t, locale } = useI18n()
const route = useRoute()
const listClients = useListClientsUseCase()
const listClientSheetRows = useListClientSheetRowsUseCase()

const { data: clients, pending: clientsPending, error: clientsError } = await useAsyncData<
  Client[]
>('sheets-clients', () => listClients.execute())

const {
  data: rowsByClient,
  pending: rowsPending,
  error: rowsError
} = await useAsyncData<Record<string, SheetRow[]>>(
  'sheets-rows-by-client',
  async () => {
    const entries = await Promise.all(
      (clients.value ?? []).map(
        async client => [client.id, await listClientSheetRows.execute(client.id)] as const
      )
    )
    return Object.fromEntries(entries)
  },
  { watch: [clients] }
)

const initialClientId = typeof route.query.clientId === 'string' ? route.query.clientId : null
const selectedClientId = ref<string | null>(initialClientId)

watchEffect(() => {
  if (!selectedClientId.value && clients.value?.length) {
    selectedClientId.value = clients.value[0]!.id
  }
})

function selectClient(clientId: string) {
  selectedClientId.value = clientId
  void navigateTo({ query: { ...route.query, clientId } })
}

const selectedClient = computed(
  () => clients.value?.find(client => client.id === selectedClientId.value) ?? null
)

const selectedRows = computed<SheetRow[]>(() => {
  if (!selectedClientId.value || !rowsByClient.value) return []
  return rowsByClient.value[selectedClientId.value] ?? []
})

function rowCountFor(clientId: string): number {
  return rowsByClient.value?.[clientId]?.length ?? 0
}

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/

function formatDate(value: string): string {
  if (!value) return ''

  const dateOnlyMatch = DATE_ONLY.exec(value)
  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch
    const parsed = new Date(Number(year), Number(month) - 1, Number(day))
    return new Intl.DateTimeFormat(locale.value).format(parsed)
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat(locale.value).format(parsed)
}

function formatAmount(value: string): string {
  if (!value) return ''
  const parsed = Number(value)
  if (Number.isNaN(parsed)) return value
  return new Intl.NumberFormat(locale.value).format(parsed)
}

const tableRows = computed(() =>
  selectedRows.value.map(row => ({
    id: row.sourceDocumentId,
    date: formatDate(row.date),
    description: row.description,
    sourceDocument: row.sourceDocumentFileName,
    amount: formatAmount(row.amount),
    tax: formatAmount(row.tax)
  }))
)

const isLoading = computed(() => clientsPending.value || rowsPending.value)
const hasError = computed(() => Boolean(clientsError.value || rowsError.value))
</script>

<template>
  <UContainer class="py-8">
    <h1 class="text-title font-bold tracking-tight">
      {{ t('sheets.title') }}
    </h1>

    <USkeleton
      v-if="isLoading"
      class="mt-6 h-40 w-full"
    />

    <p
      v-else-if="hasError"
      class="mt-6 text-small text-status-failed-fg"
    >
      {{ t('sheets.error') }}
    </p>

    <p
      v-else-if="!clients?.length"
      class="mt-6 text-small text-neutral-700"
    >
      {{ t('clients.empty') }}
    </p>

    <template v-else>
      <div class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <button
          v-for="client in clients"
          :key="client.id"
          type="button"
          class="flex flex-col gap-1 rounded-xl border border-line-100 p-4 text-left transition-colors duration-[120ms]"
          :class="
            client.id === selectedClientId
              ? 'border-transparent bg-neutral-950 text-invert'
              : 'bg-white text-neutral-900 hover:bg-paper-50'
          "
          @click="selectClient(client.id)"
        >
          <span class="text-small font-semibold">{{ client.name }}</span>
          <span
            class="font-mono text-label"
            :class="client.id === selectedClientId ? 'text-invert/55' : 'text-neutral-600'"
          >
            {{ t('sheets.rowCount', { count: rowCountFor(client.id) }) }}
          </span>
          <span
            class="text-label"
            :class="client.id === selectedClientId ? 'text-invert/55' : 'text-neutral-600'"
          >
            {{ client.spreadsheetUrl ? t('sheets.status.synced') : t('sheets.status.pendingExport') }}
          </span>
        </button>
      </div>

      <div class="mt-5 overflow-hidden rounded-xl border border-line-100 bg-white">
        <div class="flex items-center gap-3 border-b border-line-50 px-4 py-3">
          <h2 class="text-section font-semibold">
            {{ selectedClient?.name }}
          </h2>
          <span
            class="rounded-full bg-green-50 px-2.5 py-0.5 text-label font-medium text-green-700"
          >
            {{ t('sheets.rowCount', { count: selectedRows.length }) }}
          </span>

          <div class="flex-1" />

          <UButton
            v-if="selectedClient?.spreadsheetUrl"
            :to="selectedClient.spreadsheetUrl"
            target="_blank"
            variant="outline"
            icon="i-lucide-external-link"
          >
            {{ t('sheets.openInSheets') }}
          </UButton>
          <UButton
            v-else
            variant="outline"
            disabled
            icon="i-lucide-external-link"
          >
            {{ t('sheets.openInSheetsDisabled') }}
          </UButton>
        </div>

        <p
          v-if="!selectedRows.length"
          class="px-4 py-6 text-small text-neutral-700"
        >
          {{ t('sheets.emptyRows') }}
        </p>

        <UTable
          v-else
          :data="tableRows"
          :columns="[
            { accessorKey: 'date', header: t('sheets.columns.date') },
            { accessorKey: 'description', header: t('sheets.columns.description') },
            { accessorKey: 'sourceDocument', header: t('sheets.columns.sourceDocument') },
            { accessorKey: 'amount', header: t('sheets.columns.amount') },
            { accessorKey: 'tax', header: t('sheets.columns.tax') }
          ]"
        />
      </div>
    </template>
  </UContainer>
</template>
