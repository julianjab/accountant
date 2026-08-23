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
  <div class="flex flex-col gap-2">
    <template v-if="isLoading">
      <span class="text-sm text-muted">{{ t('auth.loading') }}</span>
    </template>

    <template v-else-if="isAuthenticated && user">
      <div class="flex min-w-0 items-center gap-2">
        <UAvatar
          :src="user.picture ?? undefined"
          :alt="user.name"
          size="sm"
        />
        <div
          class="min-w-0 flex-1"
          data-testid="google-auth-signed-in-as"
        >
          <p class="truncate text-[13px] font-medium text-invert">
            {{ user.name }}
          </p>
          <p class="truncate text-[11.5px] text-invert/70">
            {{ user.email }}
          </p>
        </div>
      </div>
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        block
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
