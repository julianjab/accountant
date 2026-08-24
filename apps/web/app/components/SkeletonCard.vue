<script setup lang="ts">
// Generic card-shaped placeholder for the initial loading state of any screen that
// eventually renders a `UCard`/bordered panel (document type cards, summary cards, the
// extraction panel, etc.). Kept intentionally dumb — a title bar plus N body lines — so it
// can stand in for most cards without every page inventing its own `USkeleton` combo.
withDefaults(
  defineProps<{
    lines?: number
    showHeader?: boolean
  }>(),
  { lines: 3, showHeader: true }
)
</script>

<template>
  <div class="rounded-xl border border-default bg-default p-4">
    <USkeleton
      v-if="showHeader"
      class="h-4 w-1/3"
    />
    <div
      class="flex flex-col gap-2"
      :class="showHeader ? 'mt-3' : ''"
    >
      <USkeleton
        v-for="n in lines"
        :key="n"
        class="h-3 w-full last:w-2/3"
      />
    </div>
  </div>
</template>
