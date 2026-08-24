<script setup lang="ts">
const props = defineProps<{ clientId: string }>()
const emit = defineEmits<{ imported: [] }>()

const { t } = useI18n()
const importDocuments = useImportClientDocumentsUseCase()

const running = ref(false)
const outcome = ref<string | null>(null)
const failed = ref(false)

/** Drive only reports changes made after a subscription starts, so anything
 * already sitting in the folder — or anything that arrived while no watch was
 * active — can enter no other way than by asking for it. */
async function sync() {
  running.value = true
  outcome.value = null
  failed.value = false
  try {
    const result = await importDocuments.execute(props.clientId)
    outcome.value = t('clients.detail.sync.result', {
      imported: result.imported.length,
      skipped: result.skipped,
      failed: result.failed.length + result.unreadable.length
    })
    emit('imported')
  } catch {
    failed.value = true
    outcome.value = t('clients.detail.sync.failed')
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div class="flex flex-col items-end gap-1">
    <UButton
      :label="t('clients.detail.sync.action')"
      icon="i-lucide-refresh-cw"
      size="sm"
      variant="outline"
      :loading="running"
      data-testid="sync-drive"
      @click="sync"
    />
    <p
      v-if="outcome"
      class="text-[11px]"
      :class="failed ? 'text-red-600' : 'text-muted'"
      data-testid="sync-outcome"
    >
      {{ outcome }}
    </p>
  </div>
</template>
