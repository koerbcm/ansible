# Ansible Vault Notes

The homelab inventory expects shared secrets to come from a single Ansible Vault file.

Create the shared homelab vault file here:

```bash
mkdir -p inventory/homelab/group_vars/homelab
ansible-vault create inventory/homelab/group_vars/homelab/vault.yml
```

Put this in the file:

```yaml
---
identity_client_ldap_default_authtok: "PASTE_THE_OBFUSCATED_VALUE_HERE"

base_user_password_hashes:
  koerbcm: "$6$REPLACE_WITH_YOUR_HASH"

docker2_postgresql_password: "REPLACE_WITH_THE_CURRENT_DOCKER2_POSTGRES_PASSWORD"
docker2_netdata_claim_token: "REPLACE_WITH_THE_CURRENT_DOCKER2_NETDATA_CLAIM_TOKEN"
docker2_n8n_db_password: "REPLACE_WITH_THE_CURRENT_DOCKER2_N8N_DB_PASSWORD"
docker2_n8n_smtp_password: "REPLACE_WITH_THE_CURRENT_DOCKER2_N8N_SMTP_PASSWORD"
docker1_mysql_root_password: "REPLACE_WITH_THE_CURRENT_DOCKER1_MYSQL_ROOT_PASSWORD"
docker1_mysql_app_password: "REPLACE_WITH_THE_CURRENT_DOCKER1_MYSQL_APP_PASSWORD"
docker1_nextcloud_mysql_password: "REPLACE_WITH_THE_CURRENT_DOCKER1_NEXTCLOUD_DB_PASSWORD"
docker1_nextcloud_admin_password: "REPLACE_WITH_THE_CURRENT_DOCKER1_NEXTCLOUD_ADMIN_PASSWORD"
docker1_nextcloud_smtp_password: "REPLACE_WITH_THE_CURRENT_DOCKER1_NEXTCLOUD_SMTP_PASSWORD"
docker1_graylog_password_secret: "REPLACE_WITH_THE_CURRENT_GRAYLOG_PASSWORD_SECRET"
docker1_graylog_root_password_sha2: "REPLACE_WITH_THE_CURRENT_GRAYLOG_ROOT_PASSWORD_SHA2"
docker1_graylog_transport_email_auth_username: "REPLACE_WITH_THE_CURRENT_GRAYLOG_SMTP_USERNAME"
docker1_graylog_transport_email_auth_password: "REPLACE_WITH_THE_CURRENT_GRAYLOG_SMTP_PASSWORD"

# Uptime Kuma settings (backed by 1Password item UUID:
# v74gndaweoqmvoseo6s7zo3wvi)
# Direct Kuma Socket.IO login password (recommended)
vault_uptime_kuma_password: "REPLACE_WITH_KUMA_USER_PASSWORD"

# Legacy REST-wrapper secrets (optional fallback if using mode=api)
vault_uptime_kuma_api_password: "REPLACE_WITH_KUMA_API_ADMIN_PASSWORD"
vault_uptime_kuma_api_secret_key: "REPLACE_WITH_KUMA_API_SECRET_KEY"

# Option B (optional): pre-issued bearer token flow
# If set, Ansible will skip login and use this token directly.
vault_uptime_kuma_api_access_token: ""
```

Populate the Kuma password from 1Password using `op`:

```bash
KUMA_PASSWORD="$(op item get v74gndaweoqmvoseo6s7zo3wvi --reveal --fields label=KUMA_PASSWORD)"
```

Set non-secret Kuma values in `inventory/homelab/group_vars/all.yml`:

```yaml
uptime_kuma_maintenance_mode: "socket"
uptime_kuma_server_url: "http://kuma.kirby.lan"
uptime_kuma_username: "ansible-maint"
uptime_kuma_password: "{{ vault_uptime_kuma_password }}"
uptime_kuma_api_maintenance_id: "REPLACE_WITH_MAINTENANCE_ID"
```

Install the Kuma Socket API dependency on the control node:

```bash
pip install uptime-kuma-api-v2
```

If you prefer to edit an existing file later:

```bash
ansible-vault edit inventory/homelab/group_vars/homelab/vault.yml
```

To run a playbook and be prompted for the vault password:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-playbook playbooks/site.yml --limit homelab --ask-vault-pass
```

To audit Uptime Kuma monitor coverage with the same vaulted credentials:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-playbook playbooks/uptime-kuma-audit.yml --limit docker1 --ask-vault-pass
```

If you want a local password file for convenience, create one that is ignored by git:

```bash
printf '%s\n' 'YOUR_VAULT_PASSWORD' > .vault_pass
chmod 600 .vault_pass
```

Then run:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-playbook playbooks/site.yml --limit homelab --vault-password-file .vault_pass
```

Important:

- the value in `identity_client_ldap_default_authtok` is the obfuscated LDAP token from `sssd.conf`, not the plain LDAP password
- do not commit plaintext secrets
- the shared vault is now the canonical secret location for the active homelab inventory
- app-specific secrets such as `docker2_postgresql_password`, `docker2_netdata_claim_token`, and the `docker1_nextcloud_*` values can also live in the shared homelab vault until you decide to split them later
