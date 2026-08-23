<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string
    hint?: string
    variant?: 'default' | 'success' | 'danger'
  }>(),
  { hint: undefined, variant: 'default' }
)

const VALUE_COLOR_BY_VARIANT = {
  default: 'text-highlighted',
  success: 'text-green-600',
  danger: 'text-status-failed-fg'
} as const
</script>

<template>
  <UCard :ui="{ body: 'p-3.5 sm:p-4' }">
    <div class="truncate text-[11px] font-medium uppercase tracking-[.08em] text-muted sm:text-[11.5px]">
      {{ label }}
    </div>
    <div
      class="font-mono text-[26px] font-semibold tracking-[-0.03em] sm:text-[30px]"
      :class="VALUE_COLOR_BY_VARIANT[variant]"
    >
      {{ value }}
    </div>
    <div
      v-if="hint"
      class="text-[12px] text-muted"
    >
      {{ hint }}
    </div>
  </UCard>
</template>
