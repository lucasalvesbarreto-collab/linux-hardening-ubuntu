# Audit before hardening

Run the audit script with `--phase before` to replace this placeholder with evidence.

## Servicos

| Servico | Instalado | Ativo |
|---|---|---|
| ssh | true | false |
| fail2ban | true | false |
| auditd | true | false |

## Arquivos instalados

| Arquivo | Path | Presente |
|---|---|---|
| ssh_drop_in | \etc\ssh\sshd_config.d\00-hardening.conf | false |
| sysctl | \etc\sysctl.d\99-hardening.conf | false |
| fail2ban | \etc\fail2ban\jail.local | false |
| auditd | \etc\audit\rules.d\hardening.rules | false |
| modprobe | \etc\modprobe.d\modprobe-hardening.conf | false |
