# OS Maintenance

Use `playbooks/maintenance.yml` for planned host updates. The playbook runs one host at a time.

For each host it:

1. Starts the configured pre-maintenance backup services.
2. Stops immediately if any backup service fails.
3. Refreshes apt metadata and applies Debian/Ubuntu package upgrades.
4. Runs apt autoremove and autoclean.
5. Reboots only when `/var/run/reboot-required` exists.
6. Reports Docker containers and failed systemd units after maintenance.

## Pre-Maintenance Backups

Configured services:

```text
docker1: graylog-backup-mongo.service, graylog-backup-config.service, graylog-datanode-snapshot.service, mysql-backup.service
docker2: postgresql-backup.service, n8n-backup.service, plex-backup.service
pi1: app-config-backup.service
pi2: none yet
```

Backup failures are handled by the shared `homelab-unit-failure@.service` notifier. That means a failing pre-maintenance backup should produce a `HOMELAB_ALERT` journal/syslog line and an ntfy notification when ntfy is configured.

## Commands

Run one host first:

```bash
ansible-playbook playbooks/maintenance.yml --limit pi1 --ask-become-pass
```

Run all maintenance hosts:

```bash
ansible-playbook playbooks/maintenance.yml --ask-become-pass
```

Run only backup triggers:

```bash
ansible-playbook playbooks/maintenance.yml --tags backup-trigger --ask-become-pass
```

Skip reboot even if one is required:

```bash
ansible-playbook playbooks/maintenance.yml --extra-vars os_maintenance_reboot=false --ask-become-pass
```

Resume only the OS-update portion after a mirror/network failure, without rerunning backup triggers:

```bash
ansible-playbook playbooks/maintenance.yml --limit docker2 --tags os-updates --ask-become-pass
```

The apt upgrade task retries transient mirror failures three times by default, waiting 120 seconds between attempts.

## Notes

The apt upgrade mode is `dist`, which can install or remove packages as needed inside the current OS release. It does not perform a distribution release upgrade like `do-release-upgrade`.
