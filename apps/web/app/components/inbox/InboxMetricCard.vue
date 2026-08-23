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
  <UCard :ui="{ body: 'p-4 sm:p-4' }">
    <div class="text-[11.5px] font-medium uppercase tracking-[.08em] text-muted">
      {{ label }}
    </div>
    <div
      class="font-mono text-[30px] font-semibold tracking-[-0.03em]"
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
