# Linux Hardening Ubuntu

Este repositorio fornece um conjunto básico, revisável e não destrutivo de hardening para Ubuntu Server.

> Revise as configurações antes de aplicar em produção. Mudanças incorretas em SSH podem bloquear o acesso remoto.

## Estrutura

```text
configs/
├── 00-hardening.conf        # SSH
├── jail.local               # Fail2ban
├── hardening.rules          # Auditd
├── 99-hardening.conf        # sysctl
└── modprobe-hardening.conf  # Módulos do kernel
scripts/
└── audit_hardening.py       # Auditoria local em JSON e Markdown
reports/                    # Evidências antes/depois
docs/prints/                # Capturas de tela e evidências visuais
```

## Pré-requisitos

- Ubuntu Server LTS
- `sudo`
- `openssh-server`
- Opcional: `fail2ban`, `auditd`, `lynis`

## Uso seguro

1. Faça backup das configurações existentes.
2. Confirme que há acesso alternativo ao servidor (console/IPMI).
3. Instale os componentes desejados:

```bash
sudo apt update
sudo apt install openssh-server fail2ban auditd
```

4. Valide um usuário com chave SSH ativa.
5. Copie os arquivos com cuidado:

```bash
sudo cp configs/00-hardening.conf /etc/ssh/sshd_config.d/
sudo cp configs/jail.local /etc/fail2ban/jail.local
sudo cp configs/hardening.rules /etc/audit/rules.d/hardening.rules
sudo cp configs/99-hardening.conf /etc/sysctl.d/
sudo cp configs/modprobe-hardening.conf /etc/modprobe.d/
```

6. Valide e aplique individualmente:

```bash
sudo sshd -t
sudo systemctl reload ssh || sudo systemctl reload sshd
sudo fail2ban-client -t
sudo fail2ban-client reload
sudo augenrules --load
sudo sysctl --system
```

## Auditoria

Execute antes das alterações:

```bash
sudo python3 scripts/audit_hardening.py \
  --phase before \
  --output-dir reports
```

Execute depois das alterações:

```bash
sudo python3 scripts/audit_hardening.py \
  --phase after \
  --output-dir reports
```

O script cria `audit-before.json`/`audit-after.json` e `audit-before.md`/`audit-after.md`.

## Lynis

```bash
sudo lynis audit system --no-colors
```

Salve os resultados completos em `reports/lynis-before.txt` e `reports/lynis-after.txt`.
