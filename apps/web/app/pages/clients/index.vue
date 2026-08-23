<script setup lang="ts">
import type { Client } from '~/domain/entities/client'

const { t } = useI18n()
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
</script>

<template>
  <UContainer class="py-8">
    <h1 class="text-xl font-semibold mb-4">
      {{ t('clients.title') }}
    </h1>

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
