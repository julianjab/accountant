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

// The server rejects non-https values, but the link is rendered as a plain
// <a href> — re-check here too so a stale/hand-edited value can never
// become an executable `javascript:` href.
const driveFolderUrl = computed(() => {
  const url = props.client.driveFolderUrl
  return url && url.startsWith('https://') ? url : null
})
</script>

<template>
  <!--
    Below `sm` the export action drops onto its own full-width line under the identity block:
    beside a 52px avatar and a long client name there is no room left for it, and it is the
    screen's primary action rather than a header ornament.
  -->
  <div class="mb-5 flex flex-col gap-4 sm:mb-6 sm:flex-row sm:items-start">
    <div class="flex min-w-0 flex-1 items-start gap-3 sm:gap-4">
      <div
        class="flex size-11 shrink-0 items-center justify-center rounded-[11px] bg-neutral-950 text-[16px] font-semibold text-green-400 sm:size-[52px] sm:rounded-[13px] sm:text-[18px]"
      >
        {{ initials }}
      </div>

      <div class="min-w-0 flex-1">
        <h1 class="truncate text-[21px] font-bold tracking-[-0.02em] text-highlighted sm:text-[26px]">
          {{ client.name }}
        </h1>
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-toned">
          <span class="font-mono">{{ client.taxId }}</span>
          <span class="min-w-0 truncate">{{ client.email ?? t('clients.detail.noEmail') }}</span>

          <UTooltip
            v-if="!driveFolderUrl"
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
            :to="driveFolderUrl"
            target="_blank"
            rel="noopener noreferrer"
          />
        </div>
      </div>
    </div>

    <ExportSpreadsheetButton class="shrink-0 sm:self-start" />
  </div>
</template>
