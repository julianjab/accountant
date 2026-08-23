<script setup lang="ts">
const { t } = useI18n()
const { toggle } = useMobileNav()
</script>

<template>
  <!--
    Sticky below `lg` so the drawer toggle stays reachable while the document scrolls; from
    `lg` up the shell scrolls `<main>` instead, and the topbar is already pinned by the layout.
  -->
  <header
    class="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-default bg-default px-4 sm:h-16 sm:gap-4 sm:px-6 lg:static lg:px-8"
  >
    <button
      type="button"
      class="-ml-2 flex size-10 shrink-0 items-center justify-center rounded-md text-toned transition-colors duration-[120ms] hover:bg-elevated lg:hidden"
      :aria-label="t('nav.openMenu')"
      data-testid="mobile-nav-toggle"
      @click="toggle"
    >
      <UIcon
        name="i-lucide-menu"
        class="size-5"
      />
    </button>

    <AppBreadcrumb class="min-w-0" />

    <div class="flex-1" />

    <!--
      Hidden below `md`: it is a non-interactive placeholder for a search that does not exist
      yet, and a ⌘K hint is meaningless on a touch keyboard. It comes back — and only then —
      as a real control once search is implemented.
    -->
    <div
      class="hidden w-[200px] items-center gap-2 rounded-md border border-default bg-elevated px-[11px] py-1.5 text-[12.5px] text-toned md:flex lg:w-[270px]"
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
