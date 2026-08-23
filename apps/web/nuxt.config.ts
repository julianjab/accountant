// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxtjs/i18n',
    '@nuxt/fonts'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      serverApiBase: 'http://localhost:8000'
    }
  },

  compatibilityDate: '2026-06-30',

  vite: {
    server: {
      // Vite refuses requests whose Host header it does not recognise, which
      // is what a tunnel arrives as. Quick tunnels get a new random hostname
      // every run, so the whole domain is allowed rather than one name that
      // stops being right on the next restart. Dev server only — it has no
      // effect on a build.
      allowedHosts: ['.trycloudflare.com', '.ngrok-free.app', '.ngrok.io']
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  fonts: {
    families: [
      { name: 'Public Sans', provider: 'google' },
      { name: 'JetBrains Mono', provider: 'google' }
    ]
  },

  i18n: {
    strategy: 'no_prefix',
    defaultLocale: 'es',
    locales: [
      { code: 'es', name: 'Español', file: 'es.json' },
      { code: 'en', name: 'English', file: 'en.json' }
    ]
  }
})
