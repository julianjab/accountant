<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import type { Client } from '~/domain/entities/client'

const { t } = useI18n()
const router = useRouter()
const listClients = useListClientsUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()

// Deferred and client-only on purpose: the endpoint needs the session cookie,
// which SSR does not carry, and fetching before sign-in would answer 401 and
// render as "no clients yet" — which is a different statement entirely.
const { data: clients, refresh } = await useAsyncData<Client[]>(
  'clients',
  () => listClients.execute(),
  { immediate: false, server: false, default: () => [] }
)

watch(isAuthenticated, authenticated => authenticated && refresh(), { immediate: true })

const importClients = useImportClientsUseCase()
const isImporting = ref(false)
const importError = ref(false)

async function syncWithDrive() {
  isImporting.value = true
  importError.value = false
  try {
    await importClients.execute()
    await refresh()
  } catch {
    importError.value = true
  } finally {
    isImporting.value = false
  }
}

function goToClient(id: string) {
  router.push(`/clients/${id}`)
}

function onRowSelect(_event: Event, row: Row<Client>) {
  goToClient(row.original.id)
}

// UTable marks a selectable row as role="button" tabindex="0", but Nuxt UI 4
// doesn't wire Enter/Space to activate it (only plain <button>/<a> get that for
// free) — so keyboard activation is handled here via bubbled keydown, matched
// back to the row by its native DOM index.
function onTableKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const tr = (event.target as HTMLElement).closest('tr')
  const table = tr?.closest('table')
  if (!tr || !table) return
  const headerRowCount = table.tHead?.rows.length ?? 0
  const index = tr.rowIndex - headerRowCount
  const client = index >= 0 ? clients.value?.[index] : undefined
  if (!client) return
  event.preventDefault()
  goToClient(client.id)
}
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <h1 class="text-xl font-semibold">
        {{ t('clients.title') }}
      </h1>

      <!-- Full-bleed on a phone (the only action on the screen), auto-width once it can sit
           beside the title. -->
      <UButton
        v-if="isAuthenticated"
        color="neutral"
        variant="subtle"
        size="sm"
        block
        class="sm:w-auto"
        :loading="isImporting"
        data-testid="clients-import"
        @click="syncWithDrive"
      >
        {{ t('clients.importFromDrive') }}
      </UButton>
    </div>

    <p
      v-if="importError"
      class="text-sm text-error mb-4"
      data-testid="clients-import-error"
    >
      {{ t('clients.importFailed') }}
    </p>

    <p
      v-if="isAuthLoading"
      class="text-muted"
    >
      {{ t('auth.loading') }}
    </p>

    <p
      v-else-if="!isAuthenticated"
      class="text-muted"
      data-testid="clients-signed-out"
    >
      {{ t('clients.signInRequired') }}
    </p>

    <p
      v-else-if="!clients?.length"
      class="text-muted"
    >
      {{ t('clients.empty') }}
    </p>

    <template v-else>
      <!--
        Below `sm` the same three columns become a stacked list. A table there would put the
        tax id and the email outside the viewport inside a horizontal scroller that gives no
        sign it can be scrolled — the name column alone fills the width, so nothing is visibly
        cut off. These rows are plain links, so tapping and keyboard activation come for free
        (the table needs `onTableKeydown` below to get the same).
      -->
      <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default bg-default sm:hidden">
        <li
          v-for="client in clients"
          :key="client.id"
        >
          <NuxtLink
            :to="`/clients/${client.id}`"
            class="flex min-h-14 flex-col justify-center gap-0.5 px-4 py-3 transition-colors duration-[120ms] hover:bg-elevated"
          >
            <span class="text-[13.5px] font-medium text-highlighted">{{ client.name }}</span>
            <span class="flex flex-wrap items-center gap-x-2 text-[12px] text-muted">
              <span class="font-mono">{{ client.taxId ?? '—' }}</span>
              <span class="min-w-0 truncate">{{ client.email ?? t('clients.detail.noEmail') }}</span>
            </span>
          </NuxtLink>
        </li>
      </ul>

      <UTable
        :data="clients"
        :columns="[
          { accessorKey: 'name', header: t('clients.fields.name') },
          { accessorKey: 'taxId', header: t('clients.fields.taxId') },
          { accessorKey: 'email', header: t('clients.fields.email') }
        ]"
        :on-select="onRowSelect"
        class="hidden sm:block"
        :ui="{ tr: 'cursor-pointer focus-visible:outline-2 focus-visible:outline-primary focus-visible:-outline-offset-2' }"
        @keydown="onTableKeydown"
      />
    </template>
  </UContainer>
</template>
