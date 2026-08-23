#!/usr/bin/env bash
#
# Exposes the local dev stack through Cloudflare quick tunnels, so the app can
# be opened from a phone or handed to someone else for a look.
#
# Tunnels both the web app and the API, not just the web: the browser calls the
# API directly (nuxt.config's `serverApiBase`), so a public web app pointed at
# localhost:8000 would reach the *visitor's* machine and fail on every request.
#
# Quick tunnels are public and unauthenticated at the edge. What protects the
# API is the app's own gate — every business router requires a session, and
# ACCOUNTANT_ALLOWED_SIGN_INS decides who may establish one. Do not leave this
# running unattended.

set -euo pipefail

WEB_PORT="${WEB_PORT:-3000}"
API_PORT="${API_PORT:-8000}"
RUN_DIR="${TMPDIR:-/tmp}/accountant-tunnel"

command -v cloudflared >/dev/null || {
  echo "cloudflared not found. Install it with: brew install cloudflared" >&2
  exit 1
}

mkdir -p "$RUN_DIR"
rm -f "$RUN_DIR"/*.log "$RUN_DIR"/urls.env

pids=()
cleanup() {
  echo
  echo "Closing tunnels..."
  for pid in "${pids[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

# Sets TUNNEL_URL and appends to `pids`. Deliberately not returning the URL on
# stdout: the caller would have to capture it with $(...), which runs the whole
# function in a subshell, and the PID appended there would die with it. The
# parent's `pids` would stay empty and cleanup would kill nothing — leaving
# cloudflared orphaned, still publishing the stack, exactly what this script
# warns against above.
start_tunnel() {
  local name="$1" port="$2" log="$RUN_DIR/$1.log"

  if ! nc -z localhost "$port" 2>/dev/null; then
    echo "Nothing is listening on port $port — start the $name first." >&2
    exit 1
  fi

  cloudflared tunnel --no-autoupdate --url "http://localhost:$port" >"$log" 2>&1 &
  pids+=("$!")

  # cloudflared prints the hostname a second or two after start; poll for it
  # rather than sleeping a guessed amount.
  local url=""
  for _ in $(seq 1 60); do
    url=$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$log" | head -1 || true)
    [[ -n "$url" ]] && break
    sleep 0.5
  done
  if [[ -z "$url" ]]; then
    echo "Could not read the $name tunnel URL. Full log:" >&2
    cat "$log" >&2
    exit 1
  fi
  TUNNEL_URL="$url"
}

echo "Opening tunnels..."
start_tunnel web "$WEB_PORT"
WEB_URL="$TUNNEL_URL"
start_tunnel api "$API_PORT"
API_URL="$TUNNEL_URL"

cat >"$RUN_DIR/urls.env" <<EOF
WEB_URL=$WEB_URL
API_URL=$API_URL
EOF

cat <<EOF

  Web   $WEB_URL
  API   $API_URL

Two things must change before the app works through these URLs.

1) apps/server/.env — the API and the web are now different origins, so the
   session cookie needs SameSite=None, which browsers only accept over HTTPS:

     ACCOUNTANT_WEB_APP_URL=$WEB_URL
     ACCOUNTANT_GOOGLE_OAUTH_REDIRECT_URI=$API_URL/auth/google/callback
     ACCOUNTANT_SESSION_COOKIE_SAMESITE=none
     ACCOUNTANT_SESSION_COOKIE_SECURE=true

   Then restart the API:  bun run server:serve

2) Restart the web pointing at the public API:

     NUXT_PUBLIC_SERVER_API_BASE=$API_URL bun run web:dev

Google rejects a sign-in whose redirect URI it has not been told about, so add
this one to the OAuth client in Google Cloud Console:

     $API_URL/auth/google/callback

Quick-tunnel hostnames are new on every run, so both the env values and the
Google redirect URI have to be updated each time.

Ctrl-C closes the tunnels.
EOF

wait
