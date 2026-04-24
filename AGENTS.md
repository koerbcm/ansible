# AGENTS.md - Homelab Ansible

This repo is an Ansible source of truth for a personal homelab. Keep this file short and focused on repo-specific commands, safety rules, and non-obvious operational constraints.

## Key Commands

- Syntax check main site playbook: `./scripts/ansible-playbook --syntax-check playbooks/site.yml`
- Syntax check app update workflow: `./scripts/ansible-playbook --syntax-check playbooks/app-updates.yml`
- Full dry run across active hosts: `./scripts/ansible-playbook playbooks/site.yml --limit docker1,docker2,pi1,pi2,pi4 --check --ask-become-pass`
- Apply a single app role: `./scripts/ansible-playbook playbooks/site.yml --limit HOST --tags ROLE_TAG --ask-become-pass`
- Controlled app image refresh: `./scripts/ansible-playbook playbooks/app-updates.yml --limit HOST --ask-become-pass`
- Uptime Kuma taxonomy audit: `./scripts/ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1`
- Uptime Kuma host-only deploy/check: `./scripts/ansible-playbook playbooks/uptime-kuma.yml --limit pi4 --check --ask-become-pass`
- Uptime Kuma backup deploy/check: `./scripts/ansible-playbook playbooks/uptime-kuma-backup.yml --limit pi4 --check --ask-become-pass`
- Storage audit: `./scripts/ansible-playbook playbooks/storage-audit.yml --limit docker1,docker2,pi1,pi2,pi4 --ask-become-pass`
- Storage cleanup dry run: `./scripts/ansible-playbook playbooks/storage-cleanup.yml --limit HOST --ask-become-pass`
- Maintenance window only: `./scripts/ansible-playbook playbooks/maintenance.yml --limit docker1 --tags maintenance-window --ask-become-pass`

Use `./scripts/ansible-playbook`, not the system `ansible-playbook`; the wrapper uses the repo environment and avoids known Paramiko warning noise.

## Required Checks

- Run `./scripts/ansible-playbook --syntax-check playbooks/site.yml` after playbook, role, inventory, or template edits.
- Run `./scripts/ansible-playbook --syntax-check playbooks/app-updates.yml` after app role, maintenance, backup, or update workflow edits.
- Run `git diff --check` before committing.
- For secret-related changes, verify no plaintext secrets are staged: search for `password`, `token`, `secret`, `Authorization`, private key headers, `.env`, `vpass`, `.vault_pass`, and `passwd.yaml`.

## Safety Boundaries

### Always

- Treat `inventory/homelab/` and `playbooks/` as the canonical paths.
- Keep Docker Compose files rendered from `templates/` through roles; do not make the generated host compose files authoritative.
- Use Ansible Vault for secrets. The active shared vault is `inventory/homelab/group_vars/homelab/vault.yml`.
- Preserve the maintenance-window flow for disruptive updates so Uptime Kuma does not alert through planned work.
- Use `--ask-become-pass` for plays that change remote hosts unless the user has already provided another sudo path.

### Ask First

- Deleting data directories, Docker volumes, backup roots, or anything under `/mnt/backups`.
- Changing storage paths for stateful services such as Graylog, MongoDB, PostgreSQL, MySQL, Nextcloud, Paperless, Plex, or Uptime Kuma.
- Changing monitoring DNS or the `kuma.kirby.lan` target.
- Enabling Watchtower runtime behavior or changing automatic update cadence.
- Adding new external dependencies, Python packages, or Ansible collections.

### Never

- Never commit plaintext secrets, real `.env` files, vault password files, private keys, API tokens, or generated `__pycache__`/`.pyc` files.
- Never bypass Ansible by telling the user to manually install or configure something that an existing role should own.
- Never convert missing services into ignored drift unless the host explicitly lists them in `common_service_known_absent_units`.
- Never force-push, reset hard, or revert user changes without explicit approval.

## Non-Obvious Repo Rules

- `common_services` is strict by default: services in `common_service_units` should exist after a real apply. Missing units are failures unless listed in `common_service_known_absent_units`.
- Check mode can expose package/service ordering issues because `apt` does not actually install packages. If a service is missing during check mode, run a real targeted apply for that role before treating it as host drift.
- `app-updates.yml` intentionally runs `serial: 1`, starts the Uptime Kuma maintenance window, triggers pre-update backups, pulls images, and performs post-update container health checks. Do not replace it with raw `docker compose pull && up -d` unless the user explicitly wants a manual emergency path.
- Uptime Kuma automation uses direct Socket.IO via `scripts/uptime_kuma_socket_automation.py` and requires `uptime-kuma-api-v2` on the control node.
- Uptime Kuma service deployment is now intended for `pi4` using `louislam/uptime-kuma:2.2.1`, with active data on local disk at `/srv/uptime-kuma/data` (optional one-time migration source: `/mnt/dockerVolumes/pi2/uptimeKuma_data`). Maintenance and audit hooks still target `uptime_kuma_server_url`, currently `http://kuma.kirby.lan`.
- `docker_compose_pull_policy=always` is the controlled way to refresh images through roles. Prefer the app update playbook for normal updates.
- NAS paths are acceptable backup targets; avoid using NFS as live primary storage for database/search engine state unless the role explicitly documents that design.
- Portainer is optional and non-authoritative. Ansible-rendered compose projects are the source of truth.
- Baseline NFS mounts now default to `/mnt/dockerVolumes` and `/mnt/backups` in `group_vars/all`; host vars can override/extend `nfs_mounts`.
- New-host preflight: add NAS NFS permissions before first apply (prefer subnet rules like `10.27.70.0/24`; use host-specific `/32` entries for exceptions such as temporary LAN placement).

## Adding Or Changing App Roles

When adding or materially changing an app role, keep these files aligned:

- `roles/<role>/defaults/main.yml`
- `roles/<role>/tasks/main.yml`
- `templates/<role>.compose.yml.j2`
- `inventory/homelab/hosts.yml` host group
- relevant `inventory/homelab/host_vars/<host>/main.yml`
- `playbooks/site.yml`
- `playbooks/app-updates.yml` `app_update_role_list`
- backup role or `maintenance_pre_backup_services` when the app owns important state
- Uptime Kuma expected monitor definitions when the service should be monitored

## Documentation Discipline

- Keep `AGENTS.md` focused on commands, boundaries, and hard-won gotchas. Do not duplicate broad architecture summaries from `README.md`.
- Remove stale legacy instructions instead of preserving them as parallel paths.
- If a rule stops being true, update this file in the same change as the code or inventory change.
