<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import ExportSpreadsheetButton from '~/infrastructure/components/clients/ExportSpreadsheetButton.vue'

const props = defineProps<{
  client: Client
}>()

const { t } = useI18n()

const initials = computed(() =>
  props.client.name
    .split(' ')
    .filter(word => word.length > 2)
    .slice(0, 2)
    .map(word => word[0])
    .join('')
    .toUpperCase()
)
</script>

<template>
  <div class="mb-6 flex items-start gap-4">
    <div
      class="flex size-[52px] shrink-0 items-center justify-center rounded-[13px] bg-neutral-950 text-[18px] font-semibold text-green-400"
    >
      {{ initials }}
    </div>

    <div class="min-w-0 flex-1">
      <h1 class="truncate text-[26px] font-bold tracking-[-0.02em] text-neutral-900">
        {{ client.name }}
      </h1>
      <div class="mt-1.5 flex flex-wrap items-center gap-4 text-[13px] text-neutral-700">
        <span class="font-mono">{{ client.taxId }}</span>
        <span>{{ client.email ?? t('clients.detail.noEmail') }}</span>

        <UTooltip
          v-if="!client.driveFolderUrl"
          :text="t('clients.detail.driveMissing')"
        >
          <UButton
            :label="t('clients.detail.driveOpen')"
            icon="i-lucide-folder"
            color="neutral"
            variant="outline"
            size="sm"
            disabled
          />
        </UTooltip>
        <UButton
          v-else
          :label="t('clients.detail.driveOpen')"
          icon="i-lucide-folder"
          color="neutral"
          variant="outline"
          size="sm"
          :to="client.driveFolderUrl"
          target="_blank"
          rel="noopener noreferrer"
        />
      </div>
    </div>

    <ExportSpreadsheetButton />
  </div>
</template>
