<script setup lang="ts">
import type { Client } from '~/domain/entities/client'

const { t } = useI18n()
const listClients = useListClientsUseCase()

const { data: clients } = await useAsyncData<Client[]>('clients', () => listClients.execute())
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
    />
  </UContainer>
</template>
