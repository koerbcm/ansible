# Homelab Ansible

## TL;DR

- Use the repo wrapper so Ansible runs from `.venv`:
  - `./scripts/ansible-playbook ...`
  - or enable aliases once: `source ~/workspace/tools/ansiblePersonal/scripts/ansible-aliases.zsh`
- Common runs:
  - `./scripts/ansible-playbook playbooks/site.yml --limit docker1`
  - `./scripts/ansible-playbook playbooks/maintenance.yml --limit docker1,docker2,pi1,pi2 --ask-become-pass`
  - `./scripts/ansible-playbook playbooks/app-updates.yml --limit docker1 --ask-become-pass`
  - `./scripts/ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1`
  - `./scripts/ansible-playbook playbooks/uptime-kuma-backup.yml --limit pi4 --ask-become-pass`
  - `./scripts/ansible-playbook playbooks/storage-audit.yml --limit docker1,docker2,pi1,pi2 --ask-become-pass`
- Inventory source of truth: `inventory/homelab/`
- Compose/templates source of truth: `roles/*` + `templates/`

This repo is being rebuilt so Ansible becomes the source of truth for the homelab again.

The target design is:

- `pi1` stays on Ubuntu 24.04 (ARM64)
- the long-term `pi2` role moves to a Raspberry Pi 5 on Ubuntu 24.04 (ARM64)
- the old Raspberry Pi 2 setup remains preserved as a legacy Raspberry Pi OS path for reuse or repurposing
- services are defined in this repo
- Docker compose files are rendered from templates in this repo
- NFS-backed application data is mounted by the host, not hidden inside ad hoc Docker volume definitions
- Portainer is optional, not authoritative

## Current Canonical Layout

```text
ansible.cfg
collections/requirements.yml
inventory/homelab/
  hosts.yml
  group_vars/
  host_vars/
playbooks/
  site.yml
  discovery.yml
roles/
  base/
  common_services/
  docker_engine/
  identity_client/
  legacy_cleanup/
  log_forwarder/
  netdata/
  nfs_mounts/
  ntfy/
  plex/
  portainer_agent/
  postgresql/
  discovery/
templates/
  docker-override.conf.j2
  daemon-client.json.j2
  daemon-server.json.j2
  ntfy.compose.yml.j2
docs/
  manual-discovery.md
```

The inventory under `inventory/homelab/` and the playbooks under `playbooks/` are the canonical path forward.

## What The New Roles Do

- `base`
  - installs baseline packages
  - manages local users, SSH authorized keys, and sudoers drop-ins from variables
- `docker_engine`
  - installs Docker Engine from Docker's apt repo on Debian/Ubuntu
  - preserves the existing `docker_*` variables and TLS/cert workflow you already started
  - renders daemon config from templates in this repo
- `common_services`
  - keeps baseline host services consistent across the fleet
  - currently manages `avahi-daemon`, `rsyslog`, `ufw`, and journald retention
- `nfs_mounts`
  - creates persistent host-level NFS mounts
  - writes them to `/etc/fstab` using Ansible
- `identity_client`
  - manages SSSD, LDAP client packages, and `nsswitch.conf`
  - expects the LDAP bind secret to come from Ansible Vault
- `legacy_cleanup`
  - removes obsolete host-installed services that have moved elsewhere
- `log_forwarder`
  - manages host-level `rsyslog` forwarding for nodes that should ship host logs centrally
- `netdata`
  - manages the active Netdata container on `docker2` as a compose project and preserves its host-level visibility and NFS-backed named volumes
- `portainer_agent`
  - keeps the Portainer agent managed by compose, while Portainer itself remains non-authoritative
- `plex`
  - manages the Plex Media Server compose project while preserving the current host-network and volume layout on `docker2`
- `postgresql`
  - manages the `docker2` PostgreSQL container as a compose project and preserves the current NFS-backed data path
- `ntfy`
  - renders a compose file from `templates/ntfy.compose.yml.j2`
  - deploys it with `community.docker.docker_compose_v2`
  - selects the image by architecture so ARMv7 and ARM64 can coexist cleanly
- `discovery`
  - captures the “what did I configure manually years ago?” layer into local artifacts for review

## Why This Layout Fits `pi1` + `pi2`

The hosts can run different operating systems without forking your automation:

- shared behavior lives in roles
- OS-specific differences are expressed in inventory groups and variables
- host-specific services and mount points live in `host_vars`
- the discovered application footprint can also live in `host_vars` even before each app has a dedicated role
- architecture-specific container images are selected from facts such as `ansible_architecture`

That lets `pi1` and `pi2` behave consistently without pretending they should be identical.

## Bootstrapping

Install collections used by the new playbooks:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./.venv/bin/ansible-galaxy collection install -r collections/requirements.yml
```

Run a syntax check:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook --syntax-check playbooks/site.yml
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook --syntax-check playbooks/discovery.yml
```

Run the discovery pass against an existing machine before rebuilding it:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook playbooks/discovery.yml --limit pi2
```

Discover the current active fleet:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook playbooks/discovery.yml --limit pi1,docker1,docker2
```

Discovery results can then be promoted into `host_vars` as tracked `host_application_inventory`
entries so the known service footprint stays visible while dedicated app roles are built.

### Optional Zsh Aliases

To make plain `ansible` and `ansible-playbook` automatically use this repo's wrapper scripts:

```bash
echo 'source ~/workspace/tools/ansiblePersonal/scripts/ansible-aliases.zsh' >> ~/.zshrc
source ~/.zshrc
```

You can also use the short alias:

```bash
apb playbooks/site.yml --limit docker1
```

Apply the intended state:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook playbooks/site.yml --limit pi2
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook playbooks/site.yml --limit pi1
```

Before applying to the fleet, create the shared vaulted secret file described in
[ansible-vault.md](/home/koerbcm/workspace/tools/ansiblePersonal/docs/ansible-vault.md).

Audit Uptime Kuma coverage against the codified monitor baseline:

```bash
pip install uptime-kuma-api-v2
```

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ./scripts/ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1 --ask-vault-pass
```

See [uptime-kuma-monitoring.md](/home/koerbcm/workspace/tools/ansiblePersonal/docs/uptime-kuma-monitoring.md)
for taxonomy, expected monitor coverage, maintenance-scope checks, and apply mode.
For backup and restore of local Uptime Kuma data on `pi4`, see
[uptime-kuma-backup-restore.md](/home/koerbcm/workspace/tools/ansiblePersonal/docs/uptime-kuma-backup-restore.md).

For emergency local access, you can also store a vaulted local password hash as described in
[break-glass-access.md](/home/koerbcm/workspace/tools/ansiblePersonal/docs/break-glass-access.md).
The base role now supports an optional guardrail so required local admin accounts can be forced
to keep a local password hash even when LDAP is in use.

## What Is Still Missing For Full Reproducibility

The repo structure is now ready for these, but the actual values still need to be discovered and committed:

- the real `koerbcm` SSH public keys
- sudoers exceptions and any custom groups
- LDAP / SSSD domain config and PAM/NSS behavior
- every additional containerized service besides `ntfy`
- any systemd units, timers, cron jobs, or one-off scripts
- firewall, sysctl, DNS, and network customizations
- secrets that belong in Ansible Vault instead of plaintext vars

Use [manual-discovery.md](/home/koerbcm/workspace/tools/ansiblePersonal/docs/manual-discovery.md) and `playbooks/discovery.yml` to turn those unknowns into inventory data and role inputs.

## Notes

- Logging policy:
  - Docker-managed services should ship logs through Docker's log driver only.
  - `rsyslog` should be reserved for host logs and explicit host-side file tails, not Docker container stdout/stderr.
  - Do not add remote `rsyslog` forwarding for Docker container logs unless Docker GELF is disabled for those containers.
- The old Debian 10 `libseccomp` issue on the legacy Raspberry Pi 2 goes away on the new Ubuntu 24.04 Pi 5 build, so `ntfy` should no longer need `seccomp=unconfined`.
- Adding a user to the `docker` group still grants root-equivalent control over the host. Treat that as privileged access.

## License

MIT License.
