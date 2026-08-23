<script setup lang="ts">
import type { GoogleAuthErrorCode } from '~/domain/errors/google-auth-error'

const { t } = useI18n()
const route = useRoute()
const { user, isLoading, isAuthenticated, loadSession, signIn, signOut } = useGoogleAuth()

// The callback redirects back with ?auth_error=<code> when the flow failed.
const errorKey = computed(() => {
  const code = route.query.auth_error
  return typeof code === 'string' ? `auth.errors.${code as GoogleAuthErrorCode}` : null
})

onMounted(loadSession)
</script>

<template>
  <div class="flex items-center gap-3">
    <template v-if="isLoading">
      <span class="text-sm text-muted">{{ t('auth.loading') }}</span>
    </template>

    <template v-else-if="isAuthenticated && user">
      <span
        class="text-sm text-muted"
        data-testid="google-auth-signed-in-as"
      >
        {{ t('auth.signedInAs', { email: user.email }) }}
      </span>
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        data-testid="google-auth-sign-out"
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
        data-testid="google-auth-sign-in"
        @click="signIn"
      >
        {{ t('auth.signIn') }}
      </UButton>
      <span
        v-if="errorKey"
        class="text-sm text-error"
        data-testid="google-auth-error"
      >
        {{ t(errorKey) }}
      </span>
    </template>
  </div>
</template>
