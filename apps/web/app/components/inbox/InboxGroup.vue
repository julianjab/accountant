<script setup lang="ts">
import type { Client } from '~/domain/entities/client'
import { colorForClient } from '~/utils/client-color'

const props = defineProps<{
  client: Client
  count: number
}>()

const color = computed(() => colorForClient(props.client.id))

const initials = computed(() => {
  const parts = props.client.name.trim().split(/\s+/)
  return parts.slice(0, 2).map(part => part[0]?.toUpperCase() ?? '').join('')
})
</script>

<template>
  <div>
    <div class="flex items-center gap-2 border-b border-line-50 bg-paper-50 px-4 py-2.5">
      <div
        class="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-[5px] text-[10px] font-semibold"
        :class="[color.bg, color.fg]"
      >
        {{ initials }}
      </div>
      <NuxtLink
        :to="`/clients/${client.id}`"
        class="text-[13px] font-semibold text-neutral-900 transition-colors duration-[120ms] hover:text-green-600"
      >
        {{ client.name }}
      </NuxtLink>
      <span class="font-mono text-[11.5px] text-neutral-500">
        {{ $t('inbox.group.count', { count }) }}
      </span>
    </div>
    <slot />
  </div>
</template>
