<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()

const items = computed(() => [
  { to: '/', icon: 'i-lucide-inbox', label: t('nav.inbox'), disabled: false },
  { to: '/clients', icon: 'i-lucide-users', label: t('nav.clients'), disabled: false },
  { to: '/document-types', icon: 'i-lucide-settings', label: t('nav.documentTypes'), disabled: false },
  { to: '/sheets', icon: 'i-lucide-table', label: t('nav.sheets'), disabled: true }
])

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
</script>

<template>
  <nav
    class="flex h-screen w-[238px] shrink-0 flex-col bg-neutral-950 px-3.5 pt-[22px] pb-4 text-invert"
    aria-label="main"
  >
    <div class="flex items-center gap-2.5 px-2 pb-[22px]">
      <!-- Brand placeholder: green square with "C". Replace with the real logo once one exists. -->
      <div
        class="flex h-[26px] w-[26px] items-center justify-center rounded-md bg-green-400 text-[13px] font-extrabold text-green-950"
      >
        C
      </div>
      <span class="text-[15px] font-bold tracking-[-0.01em]">{{ t('app.name') }}</span>
    </div>

    <ul class="flex flex-col gap-0.5">
      <li
        v-for="item in items"
        :key="item.to"
      >
        <span
          v-if="item.disabled"
          class="flex cursor-not-allowed items-center gap-2.5 rounded-md px-2.5 py-[9px] text-[13.5px] font-medium text-invert/35"
        >
          <UIcon
            :name="item.icon"
            class="size-4"
          />
          <span class="flex-1">{{ item.label }}</span>
        </span>

        <NuxtLink
          v-else
          :to="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          class="flex items-center gap-2.5 rounded-md px-2.5 py-[9px] text-[13.5px] font-medium text-invert/72 transition-colors duration-[120ms] hover:bg-white/[.07]"
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

    <div class="flex-1" />

    <slot name="auth" />
  </nav>
</template>
