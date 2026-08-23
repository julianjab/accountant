<script setup lang="ts">
const { t } = useI18n()
const { user, isAuthenticated, signOut } = useGoogleAuth()
</script>

<template>
  <div class="flex flex-col gap-2.5 border-t border-white/[.09] px-2.5 pt-3.5 pb-1">
    <template v-if="isAuthenticated && user">
      <div class="flex items-center gap-2.5">
        <span class="h-[26px] w-[26px] shrink-0 rounded-full border border-white/10 bg-[#1D2B24]" />

        <div class="min-w-0 flex-1">
          <p
            class="truncate text-[12.5px] text-invert"
            data-testid="sidebar-auth-email"
          >
            {{ user.email }}
          </p>
          <p class="text-[11px] text-invert/45">
            {{ t('auth.driveReadOnly') }}
          </p>
        </div>
      </div>

      <UButton
        block
        color="neutral"
        variant="outline"
        size="sm"
        class="border-white/[.12] text-invert"
        data-testid="sidebar-auth-sign-out"
        @click="signOut"
      >
        {{ t('auth.signOut') }}
      </UButton>
    </template>

    <template v-else>
      <p class="text-[12.5px] text-invert/70">
        {{ t('auth.signedOut') }}
      </p>
      <GoogleSignInButton />
    </template>
  </div>
</template>
