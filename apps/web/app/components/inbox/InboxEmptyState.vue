<script setup lang="ts">
const props = defineProps<{
  variant: 'empty' | 'no-results'
}>()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const key = computed(() => (props.variant === 'empty' ? 'empty' : 'noResults'))

function clearFilter() {
  const query = { ...route.query }
  delete query.status
  router.replace({ query })
}
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center sm:py-16">
    <p class="text-[15px] font-semibold text-highlighted">
      {{ t(`inbox.emptyState.${key}.title`) }}
    </p>
    <p class="text-[13px] text-toned">
      {{ t(`inbox.emptyState.${key}.description`) }}
    </p>
    <UButton
      v-if="variant === 'empty'"
      to="/clients"
      variant="outline"
      size="sm"
      class="mt-2"
    >
      {{ t('inbox.emptyState.empty.action') }}
    </UButton>
    <UButton
      v-else
      variant="outline"
      size="sm"
      class="mt-2"
      @click="clearFilter"
    >
      {{ t('inbox.emptyState.noResults.action') }}
    </UButton>
  </div>
</template>
