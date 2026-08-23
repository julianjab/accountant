<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <UTooltip :text="t('clients.detail.export.disabledTooltip')">
    <UButton
      :label="t('clients.detail.export.label')"
      icon="i-lucide-file-spreadsheet"
      variant="outline"
      disabled
    />
  </UTooltip>
</template>
