<script setup lang="ts">
import { GoogleAuthError } from '~/domain/errors/google-auth-error'

const { t } = useI18n()
const { user, isAuthenticated, signIn, signOut } = useGoogleAuth()

const isSigningIn = ref(false)
const errorKey = ref<string | null>(null)

async function handleSignIn() {
  isSigningIn.value = true
  errorKey.value = null

  try {
    await signIn()
  } catch (error) {
    errorKey.value = `auth.errors.${error instanceof GoogleAuthError ? error.code : 'driveDenied'}`
  } finally {
    isSigningIn.value = false
  }
}
</script>

<template>
  <div class="flex items-center gap-3">
    <template v-if="isAuthenticated && user">
      <span class="text-sm text-muted">
        {{ t('auth.signedInAs', { email: user.email }) }}
      </span>
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        @click="signOut"
      >
        {{ t('auth.signOut') }}
      </UButton>
    </template>

    <template v-else>
      <UButton
        color="primary"
        variant="solid"
        size="sm"
        :loading="isSigningIn"
        @click="handleSignIn"
      >
        {{ t('auth.signIn') }}
      </UButton>
      <span
        v-if="errorKey"
        class="text-sm text-error"
      >
        {{ t(errorKey) }}
      </span>
    </template>
  </div>
</template>
