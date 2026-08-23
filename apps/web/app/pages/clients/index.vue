<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import type { Client } from '~/domain/entities/client'

const { t } = useI18n()
const router = useRouter()
const listClients = useListClientsUseCase()

const { data: clients } = await useAsyncData<Client[]>('clients', () => listClients.execute())

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
  <UContainer class="py-8">
    <h1 class="text-xl font-semibold mb-4">
      {{ t('clients.title') }}
    </h1>

    <p
      v-if="!clients?.length"
      class="text-muted"
    >
      {{ t('clients.empty') }}
    </p>

    <UTable
      v-else
      :data="clients"
      :columns="[
        { accessorKey: 'name', header: t('clients.fields.name') },
        { accessorKey: 'taxId', header: t('clients.fields.taxId') },
        { accessorKey: 'email', header: t('clients.fields.email') }
      ]"
      :on-select="onRowSelect"
      :ui="{ tr: 'cursor-pointer focus-visible:outline-2 focus-visible:outline-primary focus-visible:-outline-offset-2' }"
      @keydown="onTableKeydown"
    />
  </UContainer>
</template>
