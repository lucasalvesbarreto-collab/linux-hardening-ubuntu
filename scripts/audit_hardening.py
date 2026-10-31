#!/usr/bin/env python3
"""
Collect local evidence for an Ubuntu hardening baseline.

This script is read-only. It does not change system configuration.
"""

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SYSCTL_CHECKS = {
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.default.accept_redirects": "0",
    "net.ipv4.conf.all.accept_source_route": "0",
    "net.ipv4.conf.default.accept_source_route": "0",
    "net.ipv4.icmp_echo_ignore_broadcasts": "1",
    "net.ipv4.tcp_syncookies": "1",
    "fs.suid_dumpable": "0",
    "kernel.kptr_restrict": "2",
    "kernel.dmesg_restrict": "1",
}

SSH_FILE = Path("/etc/ssh/sshd_config.d/00-hardening.conf")
SYSCTL_FILE = Path("/etc/sysctl.d/99-hardening.conf")
FAIL2BAN_FILE = Path("/etc/fail2ban/jail.local")
AUDIT_FILE = Path("/etc/audit/rules.d/hardening.rules")
MODPROBE_FILE = Path("/etc/modprobe.d/modprobe-hardening.conf")


def run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def service_status(name: str) -> dict[str, Any]:
    code, output = run(["systemctl", "is-active", name])
    return {"installed": code != 4, "active": code == 0, "output": output}


def check_file(path: Path) -> dict[str, Any]:
    return {
        "present": path.exists(),
        "path": str(path),
    }


def check_sysctl_values() -> dict[str, dict[str, Any]]:
    results = {}
    for key, expected in SYSCTL_CHECKS.items():
        code, output = run(["sysctl", "-n", key])
        actual = output.strip() if code == 0 else None
        results[key] = {
            "expected": expected,
            "actual": actual,
            "pass": actual == expected,
        }
    return results


def check_sshd_config() -> dict[str, Any]:
    code, effective = run(["sshd", "-T"])
    required = {
        "permitrootlogin": "no",
        "passwordauthentication": "no",
        "kbdinteractiveauthentication": "no",
        "permitemptypasswords": "no",
        "x11forwarding": "no",
        "allowtcpforwarding": "no",
    }
    effective_values = {}
    for line in effective.splitlines():
        if " " in line:
            key, value = line.split(" ", 1)
            effective_values[key.lower()] = value.lower()

    checks = {
        key: {
            "expected": expected,
            "actual": effective_values.get(key),
            "pass": effective_values.get(key) == expected,
        }
        for key, expected in required.items()
    }
    return {
        "sshd_validation": {"exit_code": code, "valid": code == 0},
        "checks": checks,
    }


def collect() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "distribution": " ".join(x for x in platform.platform().split("-") if x),
        },
        "ssh": check_sshd_config(),
        "sysctl": check_sysctl_values(),
        "services": {
            "ssh": service_status("ssh"),
            "fail2ban": service_status("fail2ban"),
            "auditd": service_status("auditd"),
        },
        "files": {
            "ssh_drop_in": check_file(SSH_FILE),
            "sysctl": check_file(SYSCTL_FILE),
            "fail2ban": check_file(FAIL2BAN_FILE),
            "auditd": check_file(AUDIT_FILE),
            "modprobe": check_file(MODPROBE_FILE),
        },
    }


def markdown_report(data: dict[str, Any]) -> str:
    lines = [
        "# Ubuntu Hardening Audit",
        "",
        f"Gerado em: `{data['timestamp']}`",
        "",
        "## SSH efetivo",
        "",
        "| Verificacao | Esperado | Atual | Resultado |",
        "|---|---|---|---|",
    ]
    ssh = data["ssh"]
    lines.append(
        f"| Configuracao SSH valida | true | {str(ssh['sshd_validation']['valid']).lower()} | "
        f"{'PASS' if ssh['sshd_validation']['valid'] else 'FAIL'} |"
    )
    for name, check in ssh["checks"].items():
        lines.append(
            f"| {name} | {check['expected']} | {check['actual'] or '-'} | "
            f"{'PASS' if check['pass'] else 'FAIL'} |"
        )

    lines.extend(["", "## sysctl", "", "| Verificacao | Esperado | Atual | Resultado |", "|---|---|---|---|"])
    for name, check in data["sysctl"].items():
        lines.append(
            f"| {name} | {check['expected']} | {check['actual'] or '-'} | "
            f"{'PASS' if check['pass'] else 'FAIL'} |"
        )

    lines.extend(["", "## Servicos", "", "| Servico | Instalado | Ativo |", "|---|---|---|"])
    for name, status in data["services"].items():
        lines.append(
            f"| {name} | {str(status['installed']).lower()} | {str(status['active']).lower()} |"
        )

    lines.extend(["", "## Arquivos instalados", "", "| Arquivo | Path | Presente |", "|---|---|---|"])
    for name, check in data["files"].items():
        lines.append(f"| {name} | {check['path']} | {str(check['present']).lower()} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita uma baseline de hardening do Ubuntu.")
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = collect()

    json_path = args.output_dir / f"audit-{args.phase}.json"
    markdown_path = args.output_dir / f"audit-{args.phase}.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(data), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
