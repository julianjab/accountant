<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()
const { isOpen, close } = useMobileNav()

const items = computed(() => [
  { to: '/', icon: 'i-lucide-inbox', label: t('nav.inbox'), disabled: false },
  { to: '/clients', icon: 'i-lucide-users', label: t('nav.clients'), disabled: false },
  { to: '/document-types', icon: 'i-lucide-settings', label: t('nav.documentTypes'), disabled: false },
  { to: '/sheets', icon: 'i-lucide-table', label: t('nav.sheets'), disabled: false }
])

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
</script>

<template>
  <!--
    Below `lg` this is a drawer: fixed, off-canvas, slid in over the page. From `lg` up the
    same element is the static rail, so there is a single sidebar instance (and a single
    mounted auth block) rather than one per breakpoint.

    `invisible` — not just the off-screen transform — is what keeps the closed drawer out of
    the tab order and the accessibility tree; `visibility` is also animatable, so the slide
    still plays. That makes the open/closed state pure CSS, with no viewport measuring.
  -->
  <nav
    class="invisible fixed inset-y-0 left-0 z-50 flex w-[268px] max-w-[85vw] shrink-0 -translate-x-full flex-col overflow-y-auto bg-neutral-950 px-3.5 pt-[22px] pb-4 text-invert transition-[transform,visibility] duration-200 ease-out lg:visible lg:static lg:h-screen lg:w-[238px] lg:max-w-none lg:translate-x-0 lg:transition-none"
    :class="isOpen ? 'visible translate-x-0' : ''"
    aria-label="main"
    data-testid="app-sidebar"
  >
    <div class="flex items-center gap-2.5 px-2 pb-[22px]">
      <!-- Brand placeholder: green square with "C". Replace with the real logo once one exists. -->
      <div
        class="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-md bg-green-400 text-[13px] font-extrabold text-green-950"
      >
        C
      </div>
      <span class="truncate text-[15px] font-bold tracking-[-0.01em]">{{ t('app.name') }}</span>

      <button
        type="button"
        class="-mr-1 ml-auto flex size-8 shrink-0 items-center justify-center rounded-md text-invert/70 transition-colors duration-[120ms] hover:bg-white/[.07] lg:hidden"
        :aria-label="t('nav.closeMenu')"
        data-testid="mobile-nav-close"
        @click="close"
      >
        <UIcon
          name="i-lucide-x"
          class="size-5"
        />
      </button>
    </div>

    <ul class="flex flex-col gap-0.5">
      <li
        v-for="item in items"
        :key="item.to"
      >
        <span
          v-if="item.disabled"
          class="flex min-h-11 cursor-not-allowed items-center gap-2.5 rounded-md px-2.5 py-[9px] text-[13.5px] font-medium text-invert/35 lg:min-h-0"
        >
          <UIcon
            :name="item.icon"
            class="size-4"
          />
          <span class="flex-1">{{ item.label }}</span>
        </span>

        <!--
          `min-h-11` below `lg`: a 44px row is the smallest comfortable touch target, while
          the desktop rail keeps its tighter 34px rhythm.
        -->
        <NuxtLink
          v-else
          :to="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          class="flex min-h-11 items-center gap-2.5 rounded-md px-2.5 py-[9px] text-[13.5px] font-medium text-invert/72 transition-colors duration-[120ms] hover:bg-white/[.07] lg:min-h-0"
          :class="isActive(item.to) ? 'bg-green-400/12 text-green-400' : ''"
        >
          <UIcon
            :name="item.icon"
            class="size-4"
          />
          <span class="flex-1">{{ item.label }}</span>
        </NuxtLink>
      </li>
    </ul>

    <div class="min-h-6 flex-1" />

    <slot name="auth" />
  </nav>
</template>
