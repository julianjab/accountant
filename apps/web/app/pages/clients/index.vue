<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import { colorForClient, initialsForClientName } from '~/utils/client-color'

const { t } = useI18n()
const listClients = useListClientsUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()

// Deferred and client-only on purpose: the endpoint needs the session cookie,
// which SSR does not carry, and fetching before sign-in would answer 401 and
// render as "no clients yet" — which is a different statement entirely.
const { data: clients, pending: clientsPending, refresh } = await useAsyncData<Client[]>(
  'clients',
  () => listClients.execute(),
  { immediate: false, server: false, default: () => [] }
)

watch(isAuthenticated, authenticated => authenticated && refresh(), { immediate: true })

// Same gap as index.vue: still loading once signed in, before `clients` has resolved.
const showSkeleton = computed(() => isAuthLoading.value || (isAuthenticated.value && clientsPending.value && !clients.value?.length))

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

    <div
      v-if="showSkeleton"
      class="overflow-hidden rounded-lg border border-default bg-default"
    >
      <SkeletonRow
        v-for="n in 5"
        :key="n"
        :trailing="false"
      />
    </div>

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

    <!--
      Same row pattern as InboxGroup/ClientDocumentList (design-system/README.md § "List row
      pattern"): a colored-initials avatar, name, and mono secondary data, one row shape at
      every width. A table here would put the tax id and email outside the viewport inside a
      horizontal scroller with no visible affordance that it scrolls — plain link rows get
      tap and keyboard activation for free instead of the row-index bookkeeping a UTable needs.
    -->
    <ul
      v-else
      class="divide-y divide-default overflow-hidden rounded-lg border border-default bg-default"
    >
      <li
        v-for="client in clients"
        :key="client.id"
      >
        <NuxtLink
          :to="`/clients/${client.id}`"
          class="flex min-h-14 items-center gap-3 px-4 py-3 transition-colors duration-[120ms] hover:bg-elevated"
        >
          <span
            class="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-[5px] text-[10px] font-semibold"
            :class="[colorForClient(client.id).bg, colorForClient(client.id).fg]"
          >
            {{ initialsForClientName(client.name) }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-[13.5px] font-medium text-highlighted">{{ client.name }}</span>
            <span class="flex flex-wrap items-center gap-x-2 text-[12px] text-muted">
              <span class="font-mono">{{ client.taxId ?? '—' }}</span>
              <span class="min-w-0 truncate">{{ client.email ?? t('clients.detail.noEmail') }}</span>
            </span>
          </span>
        </NuxtLink>
      </li>
    </ul>
  </UContainer>
</template>
