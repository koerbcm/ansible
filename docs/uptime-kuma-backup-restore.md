# Uptime Kuma Backup And Restore

This repo manages a scheduled Uptime Kuma backup on `pi4` with:

- systemd service: `uptime-kuma-backup.service`
- systemd timer: `uptime-kuma-backup.timer`
- backup root: `/mnt/backups/pi4/uptime-kuma`

The backup script archives:

- `uptime-kuma-data.tar.gz` from `/srv/uptime-kuma/data`
- optional `uptime-kuma-project.tar.gz` from `/opt/stacks/uptime-kuma`
- `backup-meta.txt` and `SHA256SUMS`

By default the script briefly stops the container to ensure SQLite consistency,
then starts it again.

## Manual Backup

```bash
sudo systemctl start uptime-kuma-backup.service
sudo systemctl status --no-pager uptime-kuma-backup.service
ls -lah /mnt/backups/pi4/uptime-kuma | tail -n 5
```

## Verify Timer

```bash
systemctl list-timers --all | grep uptime-kuma-backup
systemctl status --no-pager uptime-kuma-backup.timer
```

## Restore On Same Or New Host

1. Stop Uptime Kuma container.
2. Clear the target data directory.
3. Extract `uptime-kuma-data.tar.gz` into `/srv/uptime-kuma/data`.
4. Ensure ownership matches the configured runtime UID/GID (`1000:1000` here).
5. Start Uptime Kuma.

Example:

```bash
sudo docker stop uptime-kuma || true
sudo rm -rf /srv/uptime-kuma/data/*
sudo tar -C /srv/uptime-kuma/data -xzf /mnt/backups/pi4/uptime-kuma/<timestamp>/uptime-kuma-data.tar.gz
sudo chown -R 1000:1000 /srv/uptime-kuma/data
sudo docker start uptime-kuma
```

After restore, confirm monitor history/settings in the UI and run:

```bash
./scripts/ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1
```
