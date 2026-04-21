# Uptime Kuma Monitoring Baseline

This repo now includes a codified Uptime Kuma monitoring baseline and an audit
playbook.

## What Is Codified

- expected monitor taxonomy (`External`, `Internal`, `Docker`, `Media`)
- expected host/tier/surface tags
- expected monitor coverage for managed services on:
  - `docker1`
  - `docker2`
  - `pi1`
  - `pi2`
- expected maintenance scope attachments for:
  - `Ansible Planned Maintenance`
  - `Docker Container Updates`

Source file:

- [uptime_kuma_monitoring.yml](/home/koerbcm/workspace/tools/ansiblePersonal/inventory/homelab/group_vars/homelab/uptime_kuma_monitoring.yml)

## Run The Audit

Install dependency on the Ansible control node first:

```bash
pip install uptime-kuma-api-v2
```

```bash
ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1 --ask-vault-pass
```

This audits via the Kuma API and reports:

- missing expected tags
- missing expected monitors
- monitors missing required tags
- missing maintenance definitions
- maintenance scope gaps
- untagged non-group monitors
- unexpected monitors

The audit now uses direct Socket.IO access to Kuma (via `uptime-kuma-api-v2`)
instead of the REST wrapper service.

## Run In Apply Mode

Apply mode can safely do three things:

- create missing expected tags
- add missing required tags to existing monitors
- move existing monitors into expected parent groups (`External`, `Internal`, `Docker`, `Media`)
- normalize child monitor names to leaf names (for example `Internal / Foo` -> `Foo` under `Internal`)
- attach existing monitors to expected maintenance scopes

It can also create missing monitors, but only for expected monitor entries that
define an explicit `create_payload` (disabled by default).

One-shot apply run:

```bash
ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1 --ask-vault-pass -e uptime_kuma_monitor_audit_apply_mode=true
```

By default, unresolved apply errors fail the play
(`uptime_kuma_monitor_audit_apply_fail_on_api_errors: true`).

Then immediately rerun audit mode (without apply) to see post-apply gaps:

```bash
ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1 --ask-vault-pass
```

The audit is non-blocking by default. To make it policy-enforcing, set one or
more of these to `true` in inventory:

- `uptime_kuma_monitor_audit_fail_on_missing_tags`
- `uptime_kuma_monitor_audit_fail_on_missing_monitors`
- `uptime_kuma_monitor_audit_fail_on_monitor_tag_gaps`
- `uptime_kuma_monitor_audit_fail_on_maintenance_scope_gaps`

## Practical Next Steps

1. Add missing monitors reported by the audit, starting with `critical` tier.
2. Normalize host tags (notably `docker2` and `pi2` assignments).
3. Decide whether to keep both maintenance windows or retire one to reduce
   operator confusion.
4. Add backup freshness monitors (or push checks) and tag them with `backup`.
