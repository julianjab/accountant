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

## Google login

A user signs in with their own Google account to grant read access to their Drive
(`drive.readonly`, plus `openid email profile`). The flow is **authorization-code**, handled
end to end by `apps/server`:

1. The button sends the browser to `GET /auth/google/login` on the server, which redirects to
   Google's consent screen with a `state` nonce stored in a short-lived cookie.
2. Google redirects back to `GET /auth/google/callback`, which verifies `state`, exchanges the
   code for an access **and refresh** token, stores them server-side, and sets an httpOnly
   session cookie.
3. This app calls `GET /auth/google/me` with `credentials: 'include'` to learn who is signed in.

The access token never reaches the browser, so there is nothing here for an XSS to steal, and
the session survives reloads and browser restarts — the server renews the access token from the
refresh token whenever it has expired.

### Setup

Config lives on the server; see `apps/server/.env.example` for the full list. In the
[Google Cloud Console](https://console.cloud.google.com/apis/credentials) you need a **Web
application** OAuth client with:

- **Authorized redirect URIs**: `http://localhost:8000/auth/google/callback`
- **Authorized JavaScript origins**: not needed any more (no browser-side Google SDK)

Then set `ACCOUNTANT_GOOGLE_OAUTH_CLIENT_ID` and `ACCOUNTANT_GOOGLE_OAUTH_CLIENT_SECRET` in
`apps/server/.env`. While the app is unverified, add your account as a **test user** on the
OAuth consent screen — `drive.readonly` is a sensitive scope.

This app only needs `NUXT_PUBLIC_SERVER_API_BASE` (see `.env.example`).

### Not implemented yet

Picking files from Drive, uploading documents, and exporting to Sheets. The login currently
establishes the grant; acting on it server-side is the next step.
