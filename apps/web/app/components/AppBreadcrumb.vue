<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()

const NAV_LABEL_KEYS: Record<string, string> = {
  'clients': 'nav.clients',
  'document-types': 'nav.documentTypes',
  'sheets': 'nav.sheets'
}

const crumbs = computed(() => {
  const segments = route.path.split('/').filter(Boolean)

  const labels = segments.map((segment) => {
    const key = NAV_LABEL_KEYS[segment]
    return key ? t(key) : segment
  })

  return [t('breadcrumb.home'), ...labels]
})
</script>

<template>
  <nav aria-label="breadcrumb">
    <ol class="flex items-center gap-1.5 font-mono text-xs lowercase text-neutral-700">
      <li
        v-for="(crumb, index) in crumbs"
        :key="index"
        class="flex items-center gap-1.5"
      >
        <span v-if="index > 0">/</span>
        <span>{{ crumb }}</span>
      </li>
    </ol>
  </nav>
</template>
