#!/usr/bin/env python3
"""
Script de déploiement automatisé de myKairn SciWatch vers la VM Freebox Delta (192.168.1.170).
- Archive le projet local (src/, profiles/, systemd/, reports/, data/, pyproject.toml, README.md, Makefile)
- Transfère l'archive via SCP vers /tmp/mykairn-sciwatch-bundle.tar.gz sur la VM Freebox
- Décompresse dans /opt/mykairn-sciwatch et installe le binaire CLI /usr/local/bin/sciwatch
- Installe et active les unités systemd :
    * mykairn-sciwatch-web.service (Dashboard Web permanent sur le port 8090)
    * mykairn-sciwatch-watch.service & .timer (Veille scientifique planifiée)
"""

from __future__ import annotations

import argparse
import base64
import os
import pty
import select
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VM_IP = os.environ.get("FREEBOX_VM_HOST", "192.168.1.170")
VM_USER = os.environ.get("FREEBOX_VM_USER", "freebox")
VM_PASS = os.environ.get("FREEBOX_VM_PASS", "").strip()
VM_TARGET_DIR = os.environ.get("FREEBOX_VM_DIR", "/opt/mykairn-sciwatch")


def build_project_tarball(tar_path: Path) -> None:
    """Crée une archive tar.gz sur disque contenant les fichiers du projet et les rapports initiaux."""
    include_paths = [
        "pyproject.toml",
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "Makefile",
        ".env.example",
        "src",
        "profiles",
        "systemd",
        "tests",
        "reports",
        "data",
    ]
    with tarfile.open(str(tar_path), mode="w:gz") as tar:
        for rel in include_paths:
            full_path = ROOT_DIR / rel
            if full_path.exists():
                tar.add(str(full_path), arcname=rel)


def run_pty_process(argv: list[str], timeout: int = 180) -> str:
    """Exécute une commande interactive (ssh/scp) avec saisie automatique du mot de passe SSH via PTY."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(argv[0], argv)

    output = bytearray()
    pw_sent = False
    start = time.time()
    while time.time() - start < timeout:
        r, _, _ = select.select([fd], [], [], 0.5)
        if fd in r:
            try:
                data = os.read(fd, 4096)
                if not data:
                    break
                output.extend(data)
                if not pw_sent and b"password:" in output.lower():
                    os.write(fd, (VM_PASS + "\n").encode("utf-8"))
                    pw_sent = True
            except OSError:
                break
    os.close(fd)
    os.waitpid(pid, 0)
    return output.decode("utf-8", errors="replace")


def run_remote_cmd(argv: list[str], timeout: int = 180) -> str:
    """Exécute ssh/scp via clé SSH par défaut ou PTY si FREEBOX_VM_PASS est explicitement défini."""
    if not VM_PASS:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Commande SSH/SCP échouée (code {proc.returncode}). "
                "Configurez une clé SSH ~/.ssh/id_ed25519 ou définissez FREEBOX_VM_PASS.\n"
                + proc.stdout
            )
        return proc.stdout
    return run_pty_process(argv, timeout=timeout)


def deploy_to_vm(run_initial_audit: bool = False) -> None:
    print(f"📦 Empaquetage de myKairn SciWatch depuis {ROOT_DIR}...")
    with tempfile.NamedTemporaryFile(prefix="mykairn-sciwatch-", suffix=".tar.gz", delete=False) as tmp:
        local_tar = Path(tmp.name)

    ssh_auth_opts = (
        ["-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no"]
        if VM_PASS
        else ["-o", "BatchMode=yes"]
    )
    sudo_prefix = f"echo '{VM_PASS}' | sudo -S " if VM_PASS else "sudo "

    try:
        build_project_tarball(local_tar)
        size_kb = local_tar.stat().st_size / 1024
        print(f"🚀 Transfert SCP ({size_kb:.1f} Ko) vers {VM_USER}@{VM_IP}:/tmp/sciwatch.tar.gz...")

        # Libération préventive des caches système (journaux systemd & cache APT) sur la VM Freebox (disque 2.4 Go)
        pre_clean_cmd = (
            f"{sudo_prefix}journalctl --vacuum-size=15M >/dev/null 2>&1; "
            f"{sudo_prefix}apt-get clean >/dev/null 2>&1; "
            f"{sudo_prefix}rm -rf /var/lib/apt/lists/* /var/log/*.gz /var/log/*.[0-9] /tmp/sciwatch.tar.gz /tmp/mykairn* >/dev/null 2>&1; "
            f"df -h /"
        )
        run_remote_cmd(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                *ssh_auth_opts,
                f"{VM_USER}@{VM_IP}",
                pre_clean_cmd,
            ],
            timeout=30,
        )

        scp_argv = [
            "scp",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            *ssh_auth_opts,
            str(local_tar),
            f"{VM_USER}@{VM_IP}:/tmp/sciwatch.tar.gz",
        ]
        scp_out = run_remote_cmd(scp_argv, timeout=60)
        print(scp_out.strip())

        wrapper_script = (
            "#!/usr/bin/env bash\n"
            f"cd {VM_TARGET_DIR} && PYTHONPATH={VM_TARGET_DIR}/src exec /usr/bin/python3 -m mykairn_sciwatch \"$@\"\n"
        )
        wrapper_b64 = base64.b64encode(wrapper_script.encode("utf-8")).decode("ascii")

        audit_step = ""
        if run_initial_audit:
            audit_step = (
                f" && cd {VM_TARGET_DIR} && "
                f"PYTHONPATH={VM_TARGET_DIR}/src /usr/bin/python3 -m mykairn_sciwatch audit "
                f"--profile trail_running_coaching --max-per-source 16"
            )

        remote_cmd = (
            f"{sudo_prefix}mkdir -p {VM_TARGET_DIR}/data {VM_TARGET_DIR}/reports && "
            f"{sudo_prefix}chown -R {VM_USER}:{VM_USER} {VM_TARGET_DIR} && "
            f"tar -xzf /tmp/sciwatch.tar.gz -C {VM_TARGET_DIR} && "
            f"rm -f /tmp/sciwatch.tar.gz && "
            f"echo '{wrapper_b64}' | base64 -d | {sudo_prefix}tee /usr/local/bin/sciwatch > /dev/null && "
            f"{sudo_prefix}chmod +x /usr/local/bin/sciwatch && "
            f"{sudo_prefix}cp {VM_TARGET_DIR}/systemd/mykairn-sciwatch-web.service /etc/systemd/system/ && "
            f"{sudo_prefix}cp {VM_TARGET_DIR}/systemd/mykairn-sciwatch-watch.service /etc/systemd/system/ && "
            f"{sudo_prefix}cp {VM_TARGET_DIR}/systemd/mykairn-sciwatch-watch.timer /etc/systemd/system/ && "
            f"{sudo_prefix}systemctl daemon-reload && "
            f"{sudo_prefix}systemctl enable --now mykairn-sciwatch-web.service && "
            f"{sudo_prefix}systemctl enable --now mykairn-sciwatch-watch.timer && "
            f"{sudo_prefix}systemctl restart mykairn-sciwatch-web.service"
            f"{audit_step} && "
            f"{sudo_prefix}systemctl is-active mykairn-sciwatch-web.service && "
            f"{sudo_prefix}systemctl is-active mykairn-sciwatch-watch.timer"
        )

        ssh_argv = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            *ssh_auth_opts,
            f"{VM_USER}@{VM_IP}",
            remote_cmd,
        ]
        out = run_remote_cmd(ssh_argv, timeout=180)
        print(out)
        print(f"✅ Déploiement terminé ! Dashboard accessible sur : http://{VM_IP}:8095")
    finally:
        if local_tar.exists():
            local_tar.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Déployer myKairn SciWatch sur la VM Freebox")
    parser.add_argument(
        "--run-audit",
        action="store_true",
        help="Relancer un Audit État de l'Art Trail Running directement sur la VM après déploiement",
    )
    args = parser.parse_args()
    deploy_to_vm(run_initial_audit=args.run_audit)
