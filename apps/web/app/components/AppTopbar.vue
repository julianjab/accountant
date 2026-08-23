<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <header class="flex h-16 shrink-0 items-center gap-4 border-b border-default bg-default px-8">
    <AppBreadcrumb />

    <div class="flex-1" />

    <div
      class="flex w-[270px] items-center gap-2 rounded-md border border-default bg-elevated px-[11px] py-1.5 text-[12.5px] text-toned"
    >
      <UIcon
        name="i-lucide-search"
        class="size-4 shrink-0"
      />
      <span class="truncate">{{ t('topbar.search') }}</span>
      <span class="ml-auto rounded border border-default px-1.5 py-0.5 font-mono text-[10px] text-muted">⌘K</span>
    </div>

    <slot name="actions" />
  </header>
</template>
