<script setup lang="ts">
const { t, locale } = useI18n()

useHead({
  htmlAttrs: { lang: locale }
})

useSeoMeta({
  title: t('app.name')
})
</script>

<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
