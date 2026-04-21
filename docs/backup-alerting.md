# Backup Failure Alerting

Backup jobs are systemd oneshot services triggered by timers. Each managed backup service includes an `OnFailure=` hook that starts `homelab-unit-failure@...service` when the backup exits non-zero.

The failure handler always writes a local syslog/journal line like:

```text
HOMELAB_ALERT unit_failed host=pi1.kirby.lan unit=app-config-backup.service
```

If the host forwards logs to Graylog, search for:

```text
HOMELAB_ALERT
```

or:

```text
HOMELAB_ALERT AND unit_failed
```

## ntfy

ntfy delivery is optional. Set these vars when ready:

```yaml
vault_homelab_failure_notify_ntfy_url: "https://ntfy.example.com/homelab-alerts"
vault_homelab_failure_notify_ntfy_token: "optional-token-if-required"
```

If ntfy delivery fails, the handler logs another `HOMELAB_ALERT ntfy_notify_failed ...` line so Graylog can still catch the problem.

## Local Checks

Useful commands:

```bash
systemctl status app-config-backup.service
journalctl -u app-config-backup.service -n 100 --no-pager
journalctl -t homelab-alert -n 100 --no-pager
```

The alerting role is installed on every homelab host, including `pi2`, even if the host does not currently have backup timers.
