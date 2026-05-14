# Shlink + Uptime Kuma

Self-hosted Shlink link shortener with an Uptime Kuma bridge that auto-creates
HTTP monitors for every short URL.

## Bring-up

```sh
cd shlink
docker compose up -d --build
```

First boot order matters because Kuma needs a manual admin setup before the
bridge can log in:

1. `docker compose up -d --build` — starts everything. The `shlink_kuma_bridge`
   container will print errors and retry every `POLL_INTERVAL` seconds until
   step 2 is done; that's expected.
2. Open Kuma at <http://localhost:3001> and create the admin account using
   **exactly** the same `KUMA_USER` / `KUMA_PASS` values from `.env`.
3. The bridge will pick up the credentials on the next poll cycle — no restart
   needed.

## Endpoints

| URL | What | Auth |
| --- | --- | --- |
| <http://localhost:8080> | Shlink redirect + REST API (`/rest/v3/...`) | API key for `/rest/`, public for `/<shortCode>` |
| <http://localhost:8081> | Shlink Web Dashboard (auto-connected to API) | Basic auth (`NGINX_USER` / `NGINX_PASS`) |
| <http://localhost:3001> | Uptime Kuma | Whatever you set in step 2 |

The dashboard is pre-configured with the API server via
`shlink/web/servers.json.template`, so you should NOT have to add a server
manually. If you ever see "Server not found" inside the dashboard, check that
`SHLINK_PUBLIC_URL` in `.env` is reachable **from your browser** (not from the
docker network — i.e. don't use `http://shlink:8080`).

## Common gotchas

- `http://localhost:8080/` returns "Not found" — that's normal. Shlink only
  responds at `/<shortCode>` (redirects) and `/rest/...` (API). Use the
  dashboard at `:8081` to create short URLs.
- Bridge logs `[!] Error: ...` on first start — see step 2 above.
- Changed the API key in `.env`? `docker compose up -d --build shlink_web` to
  regenerate the dashboard's `servers.json`.
