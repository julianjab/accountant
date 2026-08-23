# Nuxt Starter Template

[![Nuxt UI](https://img.shields.io/badge/Made%20with-Nuxt%20UI-00DC82?logo=nuxt&labelColor=020420)](https://ui.nuxt.com)

Use this template to get started with [Nuxt UI](https://ui.nuxt.com) quickly.

- [Live demo](https://starter-template.nuxt.dev/)
- [Documentation](https://ui.nuxt.com/docs/getting-started/installation/nuxt)

<a href="https://starter-template.nuxt.dev/" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://ui.nuxt.com/assets/templates/nuxt/starter-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://ui.nuxt.com/assets/templates/nuxt/starter-light.png">
    <img alt="Nuxt Starter Template" src="https://ui.nuxt.com/assets/templates/nuxt/starter-light.png" width="830" height="466">
  </picture>
</a>

> The starter template for Vue is on https://github.com/nuxt-ui-templates/starter-vue.

## Quick Start

```bash [Terminal]
npm create nuxt@latest -- -t ui
```

## Deploy your own

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-name=starter&repository-url=https%3A%2F%2Fgithub.com%2Fnuxt-ui-templates%2Fstarter&demo-image=https%3A%2F%2Fui.nuxt.com%2Fassets%2Ftemplates%2Fnuxt%2Fstarter-dark.png&demo-url=https%3A%2F%2Fstarter-template.nuxt.dev%2F&demo-title=Nuxt%20Starter%20Template&demo-description=A%20minimal%20template%20to%20get%20started%20with%20Nuxt%20UI.)

## Setup

Make sure to install the dependencies:

```bash
pnpm install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
pnpm dev
```

## Production

Build the application for production:

```bash
pnpm build
```

Locally preview production build:

```bash
pnpm preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.

## Renovate integration

Install [Renovate GitHub app](https://github.com/apps/renovate/installations/select_target) on your repository and you are good to go.

## Google login (Drive read access)

The app lets a user sign in with their own Google account, from the browser, to read their
Google Drive (scope `drive.readonly`, plus `openid email profile` so the sign-in flow can show
who's logged in via `oauth2/v3/userinfo`). This is separate from the server's service account,
which is only used for the Drive webhook that processes uploaded documents.

### Create an OAuth Client ID

1. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), open (or create)
   the project used for this app.
2. Configure the **OAuth consent screen** if you haven't yet (External or Internal, depending on
   your Workspace setup). Add your own Google account as a **test user** while the app is
   unverified — Google flags `drive.readonly` as a sensitive scope, so production use will
   eventually require app verification.
3. Go to **Credentials → Create credentials → OAuth client ID**.
4. Application type: **Web application**.
5. **Authorized JavaScript origins**: add `http://localhost:3000` for local development (add your
   deployed origin(s) too, once you have one). No redirect URI is needed — this flow uses the
   Google Identity Services token client (implicit, browser-only), not the redirect-based flow.
6. Copy the generated **Client ID**.

### Configure the environment variable

Set it as `NUXT_PUBLIC_GOOGLE_CLIENT_ID` in an `.env` file inside `apps/web/`, which maps to
`runtimeConfig.public.googleClientId` in `nuxt.config.ts`:

```bash
NUXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### What this covers today (and what's next)

- Sign-in happens entirely in the browser via Google Identity Services
  (`app/infrastructure/auth/gis-google-auth-provider.ts`); the resulting `access_token` is only
  ever used client-side, and never sent to `apps/server`.
- There's no refresh token (implicit flow doesn't issue one) — the adapter tracks the token's
  `expires_in` and renews it with a silent `requestAccessToken({ prompt: '' })` call once it's
  close to expiring, and the session itself doesn't persist across page reloads beyond what
  Google Identity Services offers natively.
- Because the token lives in the browser, any XSS on this app would expose it — this is why the
  scope is read-only. Moving to an authorization-code flow with a backend-held refresh token (so
  `apps/server` can act on the user's behalf, and so the token isn't exposed to the page at all)
  is a natural next step, but out of scope for this iteration.
- Picking files from Drive (Drive Picker), uploading documents, and exporting to Sheets are not
  implemented yet — this only wires up the login and a smoke-tested read call
  (`GET drive/v3/about`).

## Document review (`/documents/[id]`)

The original-document preview in `DocumentViewer.vue` embeds Google's own `/preview` and
`/thumbnail` URLs directly (no Drive API call, no OAuth token attached to the request). This only
renders if the signed-in Google account (or "anyone with the link") has access to that specific
Drive file — a systematic 403/blank preview means the file's sharing settings need to be fixed on
the Drive side (`GoogleDriveStorage` in `apps/server`), which is out of scope here and tracked as
a follow-up.
