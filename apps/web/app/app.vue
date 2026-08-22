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
    <UHeader>
      <template #left>
        <NuxtLink
          to="/"
          class="font-semibold"
        >
          {{ t('app.name') }}
        </NuxtLink>
      </template>

      <template #right>
        <UColorModeButton />
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>
  </UApp>
</template>
