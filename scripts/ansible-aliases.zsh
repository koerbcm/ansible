# Source this file from ~/.zshrc to use repo-local Ansible wrappers by default.
# Optional override if your repo lives elsewhere:
#   export ANSIBLE_PERSONAL_ROOT=/path/to/ansiblePersonal

typeset -g ANSIBLE_PERSONAL_ROOT="${ANSIBLE_PERSONAL_ROOT:-$HOME/workspace/tools/ansiblePersonal}"

if [[ ! -x "${ANSIBLE_PERSONAL_ROOT}/scripts/ansible-playbook" ]]; then
  echo "Warning: ${ANSIBLE_PERSONAL_ROOT}/scripts/ansible-playbook not found or not executable." >&2
fi

alias ansible="${ANSIBLE_PERSONAL_ROOT}/scripts/ansible"
alias ansible-playbook="${ANSIBLE_PERSONAL_ROOT}/scripts/ansible-playbook"
alias apb="${ANSIBLE_PERSONAL_ROOT}/scripts/ansible-playbook"
