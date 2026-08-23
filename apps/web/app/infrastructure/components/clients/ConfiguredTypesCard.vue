<script setup lang="ts">
import type { DocumentType } from '~/domain/entities/document-type'

const props = defineProps<{
  types: DocumentType[]
}>()

const { t } = useI18n()

const activeCount = computed(() => props.types.filter(type => type.active).length)
</script>

<template>
  <UCard
    variant="soft"
    :ui="{ root: 'bg-neutral-950 text-invert', body: 'p-4' }"
  >
    <div class="flex items-center justify-between">
      <span class="text-[11.5px] font-medium tracking-[0.08em] text-invert/55 uppercase">
        {{ t('clients.detail.configuredTypes.title') }}
      </span>
      <span class="font-mono text-[11.5px] text-invert/55">
        {{ t('clients.detail.configuredTypes.activeCount', { count: activeCount }) }}
      </span>
    </div>

    <div
      v-if="types.length"
      class="mt-2.5 flex flex-wrap gap-1.5"
    >
      <span
        v-for="type in types"
        :key="type.id"
        class="rounded-full bg-green-400/13 px-2.5 py-[3px] text-[11.5px] text-green-300"
      >
        {{ type.name }}
      </span>
    </div>

    <!-- TODO(#12): point to the real document-type configuration route once it exists. -->
    <UButton
      class="mt-3.5"
      block
      variant="outline"
      color="neutral"
      size="sm"
      :label="t('clients.detail.configuredTypes.goToConfig')"
      to="TODO(#12)"
      :ui="{ base: 'border-white/14 text-invert' }"
    />
  </UCard>
</template>
