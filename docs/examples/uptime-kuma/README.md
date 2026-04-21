# Uptime Kuma Compose Backups

This folder stores a backup copy of the NAS-hosted compose definitions for Uptime Kuma and the Uptime Kuma REST API wrapper.

- `docs/examples/uptime-kuma/compose.yml`: Uptime Kuma service definition
- `docs/examples/uptime-kuma-api/compose.yml`: Uptime Kuma REST API wrapper definition
- `docs/examples/uptime-kuma-api/compose.local-build.yml`: local-build variant for building the wrapper from a checked-out repo
- `docs/examples/uptime-kuma-api/.env.example`: secret placeholders for API credentials

Use these files as recovery references or migration starters if the NAS copies are lost.

Note: Ansible maintenance-window and monitor-audit automation now targets Kuma
directly via Socket.IO (`uptime-kuma-api-v2`). The REST wrapper stack here is
kept only as an optional/manual integration path.

## Secret Source Note

- Uptime Kuma and Kuma API credentials are stored in 1Password.
- 1Password item UUID: `v74gndaweoqmvoseo6s7zo3wvi`
- Do not store plaintext credentials in this repository.

### Quick `op` Helper

```bash
# Fetch Kuma API admin password from the shared item UUID.
op item get v74gndaweoqmvoseo6s7zo3wvi --reveal --fields label=ADMIN_PASSWORD
```

Use a fixed `KUMA_API_SECRET_KEY` value (store it in Ansible Vault as
`vault_uptime_kuma_api_secret_key`) to avoid JWT signature churn after restarts.

## Local Build Option

If you want to run the `develop` branch before an upstream image exists, use
`docs/examples/uptime-kuma-api/compose.local-build.yml`.

1. Clone the API repo on NAS:

```bash
git clone https://github.com/MedAziz11/Uptime-Kuma-Web-API.git /volume1/dockerProjects/Uptime-Kuma-Web-API
cd /volume1/dockerProjects/Uptime-Kuma-Web-API
git checkout develop
```

2. Update the `build.context` path in `compose.local-build.yml` if needed.

3. Build and run:

```bash
docker compose -f docs/examples/uptime-kuma-api/compose.local-build.yml --env-file docs/examples/uptime-kuma-api/.env.example up -d --build
```
