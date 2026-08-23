<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <header class="flex h-[62px] shrink-0 items-center gap-4 border-b border-line-100 bg-white px-[30px]">
    <AppBreadcrumb />

    <div class="flex-1" />

    <div
      class="flex w-[270px] items-center gap-2 rounded-md border border-line-100 bg-[#F2F2EE] px-[11px] py-1.5 text-[12.5px] text-neutral-600"
    >
      <UIcon
        name="i-lucide-search"
        class="size-4 shrink-0"
      />
      <span class="truncate">{{ t('topbar.search') }}</span>
      <span class="ml-auto rounded border border-line-150 px-1.5 py-0.5 font-mono text-[10px]">⌘K</span>
    </div>

    <slot name="actions" />
  </header>
</template>
