# Manual Discovery Checklist

Use this before rebuilding a host that has been managed manually for years.

## What To Capture

- local users and service accounts
- SSH authorized keys
- sudoers files and privileged groups
- LDAP / SSSD config
- NFS mounts and `/etc/fstab`
- firewall state such as `ufw`
- rsyslog and other logging customizations
- enabled systemd units and timers
- cron jobs
- installed packages that matter operationally
- Docker containers, compose projects, and daemon settings
- custom scripts under `/usr/local`, `/opt`, and home directories

## Recommended Workflow

1. Run `playbooks/discovery.yml` against the old host.
2. Review the generated files under `artifacts/discovery/<host>/`.
3. Convert stable intent into inventory vars or role defaults.
4. Move secrets into Ansible Vault instead of plaintext vars.
5. Re-run discovery after migration to confirm nothing important was missed.

## Good Candidates For Future Roles

- `identity_client` for LDAP / SSSD / NSS / PAM
- `ssh_hardening` for sshd config and trust policy
- `systemd_units` for custom services and timers
- `compose_apps` or additional per-service roles beyond `ntfy`
- `backup_client` if these nodes need backup agent or snapshot hooks
