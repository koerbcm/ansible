# Break-Glass Local Access

Keep a local password hash for `koerbcm` so you still have emergency access if LDAP is unavailable.

This complements SSH keys and local sudo. It is not meant to replace them.

## Recommended Approach

Store a password hash in Ansible Vault, not the plaintext password.

The base role reads a mapping named `base_user_password_hashes`, keyed by username.
It also supports a small guardrail:

- `base_break_glass_users`
  - which local admin accounts must always have a local password path
- `base_require_break_glass_passwords`
  - when `true`, the play will fail if any required break-glass user is missing a local password hash

## Generate A Password Hash

If you have Python `passlib` available:

```bash
python3 - <<'PY'
from passlib.hash import sha512_crypt
print(sha512_crypt.hash(input("Password: ")))
PY
```

If `mkpasswd` is available:

```bash
mkpasswd --method=sha-512
```

The result should look like a long hash starting with something like `$6$`.

## Store The Hash In Vault

Edit the shared homelab vault file:

```bash
ansible-vault edit inventory/homelab/group_vars/homelab/vault.yml
```

Add this structure:

```yaml
---
identity_client_ldap_default_authtok: "EXISTING_OBFUSCATED_LDAP_TOKEN"

base_user_password_hashes:
  koerbcm: "$6$REPLACE_WITH_YOUR_HASH"
```

You can reuse the same hash on multiple hosts, or create different host-specific vault files later if you want different passwords.

When you are ready to make this mandatory, turn on the guardrail in inventory:

```yaml
base_break_glass_users:
  - koerbcm
base_require_break_glass_passwords: true
```

## Test Safely

No remote changes:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-inventory --host pi2 --ask-vault-pass >/dev/null && echo "vault loads correctly"
```

Dry-run the base role:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-playbook playbooks/site.yml --limit pi2 --tags base --check --ask-vault-pass
```

Validate that the break-glass requirement would pass:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible-playbook playbooks/site.yml --limit pi2 --tags base --check --ask-vault-pass -e base_require_break_glass_passwords=true
```

## Why This Helps

If LDAP is down:

- `root` still exists
- the local `koerbcm` account still exists
- SSH keys for local `koerbcm` still work
- a local password hash gives you one more recovery path through console or password auth if needed
