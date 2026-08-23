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

// No aggregate "row counts for all clients" endpoint exists yet, and every card
// shows its own count, so this inherently fans out one request per client. Cap
// how many run at once instead of firing all of them (and the Firestore reads
// behind each) in a single burst.
const ROW_FETCH_CONCURRENCY = 4

async function fetchRowsWithConcurrencyLimit(
  clientList: Client[]
): Promise<{ rowsByClient: Record<string, SheetRow[]>, failedClientIds: Set<string> }> {
  const rowsByClient: Record<string, SheetRow[]> = {}
  const failedClientIds = new Set<string>()
  let nextIndex = 0

  async function worker() {
    while (nextIndex < clientList.length) {
      const client = clientList[nextIndex++]!
      try {
        rowsByClient[client.id] = await listClientSheetRows.execute(client.id)
      } catch {
        // A per-client failure must not be conflated with "no approved rows" —
        // presenting a fetch error as an empty accounting sheet is a false negative.
        failedClientIds.add(client.id)
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(ROW_FETCH_CONCURRENCY, clientList.length) }, worker)
  )
  return { rowsByClient, failedClientIds }
}

const {
  data: rowsResult,
  pending: rowsPending,
  error: rowsError
} = await useAsyncData<{ rowsByClient: Record<string, SheetRow[]>, failedClientIds: Set<string> }>(
  'sheets-rows-by-client',
  () => fetchRowsWithConcurrencyLimit(clients.value ?? []),
  { watch: [clients] }
)

const rowsByClient = computed(() => rowsResult.value?.rowsByClient ?? {})
const failedClientIds = computed(() => rowsResult.value?.failedClientIds ?? new Set<string>())

const initialClientId = typeof route.query.clientId === 'string' ? route.query.clientId : null
const selectedClientId = ref<string | null>(initialClientId)

watchEffect(() => {
  if (!clients.value?.length) return

  const isValidSelection = clients.value.some(client => client.id === selectedClientId.value)
  if (!isValidSelection) {
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
  if (!selectedClientId.value) return []
  return rowsByClient.value[selectedClientId.value] ?? []
})

const selectedClientFailed = computed(
  () => Boolean(selectedClientId.value && failedClientIds.value.has(selectedClientId.value))
)

function rowCountFor(clientId: string): number {
  return rowsByClient.value[clientId]?.length ?? 0
}

function hasRowsErrorFor(clientId: string): boolean {
  return failedClientIds.value.has(clientId)
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
            v-if="hasRowsErrorFor(client.id)"
            class="font-mono text-label text-status-failed-fg"
          >
            {{ t('sheets.rowsUnavailable') }}
          </span>
          <span
            v-else
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
            v-if="selectedClientFailed"
            class="rounded-full bg-status-failed-bg px-2.5 py-0.5 text-label font-medium text-status-failed-fg"
          >
            {{ t('sheets.rowsUnavailable') }}
          </span>
          <span
            v-else
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
          v-if="selectedClientFailed"
          class="px-4 py-6 text-small text-status-failed-fg"
        >
          {{ t('sheets.rowsUnavailable') }}
        </p>
        <p
          v-else-if="!selectedRows.length"
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
