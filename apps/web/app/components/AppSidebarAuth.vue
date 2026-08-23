<script setup lang="ts">
const { t } = useI18n()
const { isAuthenticated } = useGoogleAuth()
</script>

<template>
  <div class="flex flex-col gap-1.5 border-t border-white/[.09] px-2.5 pt-3.5 pb-1">
    <GoogleSignInButton />
    <p
      v-if="isAuthenticated"
      class="text-[11px] text-invert/70"
    >
      {{ t('auth.driveReadOnly') }}
    </p>
  </div>
</template>
