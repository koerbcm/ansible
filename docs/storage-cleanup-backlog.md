# Storage Cleanup Backlog

This is a follow-up checklist for after all stacks are under Ansible management.

The migration pattern is moving important live state to local disk and using the NAS as the backup target. During that process, old NFS-backed Docker volumes and previous smoke-test backups can remain in place. Do not delete these casually while a service is still being migrated.

## Goals

- Confirm every active service has an intentional storage owner: local primary, NAS media mount, or backup-only NAS path.
- Confirm every important local primary dataset has a tested backup path.
- Remove or archive stale Docker volumes only after the replacement service has been stable and backups have been verified.
- Reclaim unused host disk and NAS space from retired containers, old images, and abandoned NFS-backed volumes.
- Keep routine maintenance from accumulating stale Docker artifacts long-term.

## Automated Housekeeping

`playbooks/maintenance.yml` now includes the `storage_housekeeping` role with conservative defaults:

- prune stopped containers older than `168h`
- prune dangling Docker images
- prune old Docker builder cache
- vacuum journal logs to `30d`
- run `systemd-tmpfiles --clean`

Safety defaults:

- disabled by variable only if needed (`storage_housekeeping_enabled`)
- broad deletes remain off by default (`storage_housekeeping_prune_unused_images`, `storage_housekeeping_prune_networks`, `storage_housekeeping_prune_volumes`)
- use `storage_housekeeping_apply=false` for a non-destructive audit run

## Known Items

- `docker2` has active Plex config in local Docker volume `plexConfig_data`; backup coverage is selective and excludes large rebuildable Plex cache/thumbnail directories.
- `docker2` still has old stopped Elasticsearch and Kibana containers.
- `docker2` still has invoice-ninja NFS-backed volumes with no active container.
- `docker2` still has an Obsidian image and NFS-backed volume with no active container.
- `docker2` previously wrote PostgreSQL and n8n smoke-test backups to local `/mnt/backups` before the NAS mount was added; those were cleaned up after mounting the NAS path.
- `pi1` active media/download stacks now use bind mounts from Ansible-rendered compose files, but old pre-Ansible NFS-backed named volumes still exist for Radarr, Sonarr, SABnzbd, and LazyLibrarian.
- `pi1` Radarr, Sonarr, SABnzbd, and LazyLibrarian live configs are on NAS-backed paths under `/mnt/dockerVolumes/pi1`; separate app-config backups are written to `/mnt/backups/pi1/app-config`.

## Host Audit Commands

Use these read-only commands first:

```bash
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker volume ls
docker system df -v
findmnt
```

Or run the read-only Ansible audit across the maintenance fleet:

```bash
ansible-playbook playbooks/storage-audit.yml --limit docker1,docker2,pi1,pi2 --ask-become-pass
```

This audit does not delete anything. It reports:

- backup mount source/type and capacity
- top-level backup directory sizes
- recent entries in known backup roots
- stopped containers, Docker disk usage, and unused Docker volumes
- `service_backlog` markers from host vars

For approved stale Docker volumes, run the cleanup playbook in dry-run mode first:

```bash
ansible-playbook playbooks/storage-cleanup.yml --limit pi1,docker2 --ask-become-pass
```

Then apply removals:

```bash
ansible-playbook playbooks/storage-cleanup.yml --limit pi1,docker2 --ask-become-pass -e storage_cleanup_apply=true
```

The cleanup role only removes host-approved candidate volumes and refuses to remove any candidate that is still attached to a container.

For Docker volumes, check whether a volume is attached before considering cleanup:

```bash
docker ps -a --filter volume=<volume_name> --format '{{.Names}} {{.Image}} {{.Status}}'
docker volume inspect <volume_name>
```

For mount shadowing, check whether local files exist below a mount point only when the backup services are inactive:

```bash
systemctl is-active postgresql-backup.service n8n-backup.service plex-backup.service
sudo umount /mnt/backups
sudo find /mnt/backups -maxdepth 2 -type f
sudo mount /mnt/backups
findmnt -T /mnt/backups
```

## Cleanup Rules

- Do not delete an NFS-backed Docker volume until the related service is either retired or has been running from the new Ansible-managed storage with verified backups.
- Do not use `docker system prune --volumes` on these hosts. It is too broad for this environment.
- Prefer targeted cleanup: remove one known-unused container, image, or volume at a time.
- Preserve NAS paths for retired-but-possibly-revivable apps until the app is explicitly marked `retired`.
- After any fstab or mount change, run `sudo systemctl daemon-reload`.

## Backup Retention

- Daily database and app-data backup jobs should keep at least 60 days by default.
- Daily app config backup jobs should keep at least 60 days by default.
- Config backup jobs should keep at least 90 days by default.
- Graylog DataNode/OpenSearch snapshots should keep at least 90 days by default and must be deleted through the OpenSearch snapshot API, not by removing files from the snapshot repository.
- Mirror-style backups such as Plex `config-current` do not provide historical generations by themselves; they are meant to preserve the current recoverable config state without duplicating large media/cache trees.
