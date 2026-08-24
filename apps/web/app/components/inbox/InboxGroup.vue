<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import { colorForClient, initialsForClientName } from '~/utils/client-color'

const props = defineProps<{
  client: Client
  count: number
}>()

const color = computed(() => colorForClient(props.client.id))
const initials = computed(() => initialsForClientName(props.client.name))
</script>

<template>
  <div>
    <div class="flex items-center gap-2 border-b border-default bg-elevated px-4 py-2.5">
      <div
        class="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-[5px] text-[10px] font-semibold"
        :class="[color.bg, color.fg]"
      >
        {{ initials }}
      </div>
      <NuxtLink
        :to="`/clients/${client.id}`"
        class="min-w-0 truncate text-[13px] font-semibold text-highlighted transition-colors duration-[120ms] hover:text-green-600"
      >
        {{ client.name }}
      </NuxtLink>
      <span class="shrink-0 font-mono text-[11.5px] text-muted">
        {{ $t('inbox.group.count', { count }) }}
      </span>
    </div>
    <slot />
  </div>
</template>
