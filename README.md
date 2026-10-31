# Hardening de Linux (Ubuntu Server) com auditoria automatizada em Python

Laboratório prático de endurecimento (*hardening*) de um servidor Ubuntu Server, com medição **antes e depois** usando o Lynis e um script próprio em Python que audita os controles e gera relatórios em JSON e Markdown.

> **Ambiente de laboratório.** Todo o projeto foi executado em uma VM local, sem dados reais. Hostnames, IPs e usuários dos relatórios foram substituídos por valores genéricos.

## Objetivo

- Aplicar controles de segurança baseados em boas práticas (inspirados no CIS Benchmark) em um servidor Linux.
- **Medir** o resultado de forma objetiva, com dados do antes e do depois.
- Automatizar a verificação dos controles com Python, para que a auditoria seja repetível e possa rodar em CI.
- Documentar as decisões, inclusive o que **não** foi aplicado e por quê (aceitação de risco).

## Ambiente

| Item | Detalhe |
|---|---|
| Sistema | Ubuntu Server LTS (sem interface gráfica) |
| Virtualização | VM local (2 CPUs, 2 GB RAM, 20 GB disco) |
| Acesso | SSH com chave Ed25519 |
| Auditor externo | [Lynis](https://github.com/CISOfy/lynis) |
| Script próprio | Python 3 (`scripts/audit_hardening.py`) |

## Resultados

| Medição | Antes | Depois | Variação |
|---|---|---|---|
| Lynis hardening index | 68 | 80 | +12 pontos |
| Script Python (nota %) | 48% | 100% | +52 pontos percentuais |
| Controles FAIL de severidade alta | _n_ | 0 | |

**Como interpretar.** O script chegou a 100% porque verifica os ~30 controles que eu implementei. O Lynis testa centenas de itens, por isso a nota dele é menor e é a medição mais exigente. Os itens que ficaram abertos no Lynis estão justificados na seção de decisões de risco.

Evidências: relatórios em `reports/` e capturas de tela em `docs/prints/`.

## O que foi feito

### Metodologia

1. Criação da VM, acesso por chave SSH e **snapshot** `baseline`.
2. Medição do estado inicial (**antes**) com Lynis e com o script Python.
3. Aplicação de 8 controles, com snapshot antes das mudanças críticas.
4. Medição do estado final (**depois**) com as mesmas ferramentas.
5. Análise dos itens restantes e documentação das decisões de risco.

### Controles aplicados

| # | Controle | O que foi feito | Por que importa |
|---|---|---|---|
| 1 | Atualizações automáticas | `unattended-upgrades` ativo | Correções de segurança aplicadas sem depender de ação manual |
| 2 | SSH | Login de root e senha desativados, `MaxAuthTries 3`, `AllowUsers`, banner | Elimina brute force de senha e reduz a superfície de acesso |
| 3 | Firewall | UFW com `deny incoming` e `ufw limit 22/tcp` | Só o SSH é exposto, com limite de taxa de conexões |
| 4 | Fail2ban | Jail do `sshd`, `backend = systemd`, ban de 1h | Bloqueia IPs que insistem em falhar a autenticação |
| 5 | Auditd | Regras sobre `passwd`, `shadow`, `sudoers`, `sshd_config` e `cron` | Trilha de auditoria de contas, privilégios e persistência |
| 6 | Kernel (sysctl) | Anti-spoofing, SYN cookies, ASLR, restrições de `dmesg` e ponteiros | Dificulta ataques de rede e exploração de memória |
| 7 | Senhas e contas | `pwquality` (mín. 12 caracteres) e validade em `login.defs` | Reduz risco de senhas fracas e antigas |
| 8 | Superfície de ataque | Revisão de portas (`ss`), serviços ativos, AppArmor e módulos desnecessários | Menos serviços e módulos significam menos pontos de entrada |

Os arquivos de configuração aplicados estão em `configs/`.

### Correções adicionais guiadas pelo Lynis

Depois dos 8 controles, usei as sugestões do relatório do Lynis para tratar itens adicionais, identificados pelo ID do teste:

| ID Lynis | Área | Ação |
|---|---|---|
| `FIRE-4590` | Firewall | Ajuste de firewall sugerido pelo Lynis, aplicado |
| `BOOT-5122` | Boot | Proteção do GRUB (senha no gerenciador de boot), aplicada |
| `HRDN-7222` | Hardening | Restrição de acesso aos compiladores, aplicada |

Esse ciclo (medir, corrigir, medir de novo) levou o índice do Lynis de 68 para 80.

### Script de auditoria em Python

O script `scripts/audit_hardening.py` verifica cerca de 30 controles e classifica cada um como PASS ou FAIL, com severidade (alta, média ou baixa).

| Categoria | O que verifica |
|---|---|
| SSH | Configuração **efetiva** via `sshd -T` |
| Firewall | UFW ativo |
| Serviços | Fail2ban, Auditd e atualizações automáticas ativos |
| Kernel | 10 parâmetros de `sysctl`, lidos de `/proc/sys` |
| Arquivos | Permissões e dono de `passwd`, `shadow`, `gshadow` e `sshd_config` |
| Contas | Contas com UID 0 além de root e contas com senha vazia |

**Decisões de design:**

- Os controles ficam em **tabelas de dados**: auditar algo novo é adicionar uma linha.
- Os comandos são executados com `subprocess` recebendo **lista de argumentos e sem `shell=True`**, o que evita injeção de comando.
- Se um dado não pode ser lido, o controle **reprova** (nunca dá falso PASS).
- Retorna **código de saída 1** se um controle de severidade alta falhar, o que permite uso em pipeline.

**Como executar:**

```bash
sudo python3 scripts/audit_hardening.py \
  --json reports/audit.json \
  --md reports/audit.md
```

## Estrutura do repositório

```
linux-hardening-ubuntu/
├── configs/              # configurações aplicadas (SSH, Fail2ban, Auditd, sysctl, modprobe)
├── scripts/
│   └── audit_hardening.py
├── reports/              # relatórios do Lynis e do script (antes e depois)
├── docs/prints/          # evidências
├── .github/workflows/    # Gitleaks e Bandit sobre o próprio código
└── README.md
```

## Decisões de risco (o que não foi aplicado e por quê)

Hardening não é aplicar tudo às cegas. Foram priorizados os controles de maior impacto e os demais foram avaliados caso a caso.

| Item | Decisão | Motivo |
|---|---|---|
| `net.ipv4.ip_forward = 0` | Não aplicado | Quebra Docker e VPNs; o ambiente pode precisar de encaminhamento |
| `FILE-6310` (partições separadas para `/home`, `/tmp` e `/var`) | Não aplicado | O servidor já está em funcionamento com **LVM** sobre a partição `sda3` e um volume lógico único na raiz. Reorganizar o particionamento em um sistema em uso traz risco de indisponibilidade e perda de dados, com benefício baixo neste ambiente. Em uma instalação nova, o ideal é já criar volumes lógicos separados. |
| `LOGG-2154` (envio de logs a um servidor externo) | Não aplicado | Trata-se de um **servidor de testes isolado**, sem dado real. Em produção, os logs seriam enviados a um coletor remoto (por exemplo, o Wazuh), para que um atacante não consiga apagar a evidência localmente. |

Essas decisões seguem o raciocínio de **aceitação de risco**: o impacto e a probabilidade no ambiente atual não justificam o custo ou o risco da mudança, e o motivo fica registrado.

## Lições aprendidas

- **Meça antes de mexer.** Sem o "antes", não há como provar o resultado.
- **A ordem dos arquivos de configuração importa.** No OpenSSH vale a **primeira** ocorrência de cada opção, e `sshd_config.d/` é lido em ordem alfabética. Por isso o arquivo se chama `00-hardening.conf`: um `50-cloud-init.conf` poderia reativar `PasswordAuthentication yes`.
- **Verifique a configuração efetiva, não o arquivo.** `sshd -T` mostra o que o servidor realmente usa; um `grep` pode dar falso PASS.
- **Nunca se tranque para fora.** Mantive uma sessão SSH antiga aberta, testei a nova antes de fechar a anterior, validei com `sshd -t` e tinha snapshots. Em caso de bloqueio, a recuperação é pelo **console da VM** ou pelo snapshot. Causas típicas: senha desativada antes de a chave funcionar, `AllowUsers` errado, permissões da chave, UFW sem a porta 22 ou IP banido pelo Fail2ban.
- **Ordem do firewall:** a regra do SSH vem **antes** do `ufw enable`; com `deny incoming` e sem a porta 22, a própria sessão é cortada.
- **Logs no Ubuntu recente ficam no journal do systemd.** Sem `backend = systemd`, o Fail2ban pode não enxergar as falhas e nunca banir ninguém, mesmo aparecendo como ativo.
- **Auditd é a fonte, o SIEM é a análise.** O Auditd registra os eventos no Linux (como o Sysmon faz no Windows); um SIEM como o Wazuh coleta esses logs, aplica regras e gera alertas.
- **Decisão de risco documentada vale mais que 100% às cegas.** Registrar o que não foi aplicado e o motivo demonstra critério.
- **Segurança não é uma nota.** Um script com 100% só confirma os controles que eu escolhi verificar.

## Limitações

- O script audita apenas os controles que eu implementei; não substitui o Lynis, que testa muito mais itens.
- Não cobre vulnerabilidades em software instalado (CVEs), falhas de aplicações, erros de lógica, zero-days nem o fator humano.
- Auditoria pontual: não detecta **desvios futuros** sem execução recorrente ou monitoramento.
- O hardening foi feito de forma manual; ainda não é reproduzível automaticamente.

## Próximos passos

- Instalar o **agente Wazuh** na VM e enviar os eventos do Auditd ao SIEM, com alertas para alterações em `passwd`, `sudoers` e `sshd_config` (integração com o laboratório de AD + Wazuh).
- Automatizar o hardening com **Ansible**, para torná-lo reproduzível.
- Agendar a auditoria (cron ou systemd timer) e comparar execuções para detectar desvios.
- Adicionar varredura de vulnerabilidades com **OpenVAS** ou **Trivy** no sistema de arquivos.
- Comparar os resultados com o `usg audit` (Ubuntu Security Guide) e com o CIS Benchmark oficial.

## Segurança do repositório

- Nenhuma chave privada, senha ou arquivo de `/etc/shadow` é versionado.
- O código passa por **Gitleaks** (segredos) e **Bandit** (SAST) a cada push, reaproveitando o pipeline do projeto [devsecops-pipeline-flask](https://github.com/lucasalvesbarreto-collab/devsecops-pipeline-flask).
- Relatórios foram revisados e anonimizados antes do commit.

## Referências

- [Lynis](https://cisofy.com/lynis/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks)
- [Ubuntu Server: segurança](https://ubuntu.com/server/docs)
- [OpenSSH: `sshd_config`](https://man.openbsd.org/sshd_config)

---

**Autor:** Lucas Alves Barreto · [LinkedIn](https://linkedin.com/in/lucas-alves-556693206) · [GitHub](https://github.com/lucasalvesbarreto-collab)
