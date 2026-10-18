#!/usr/bin/env python3
"""Reconcile live infrastructure state against what git says it should be.

This exists because every finding in the 2026-07-11 RedTeam audit had the
same root cause: something on disk (a VM, an orphaned service stack, a
missing node_exporter) silently diverged from what git/AGENT.md claims, and
nothing caught it until someone SSHed in by hand and looked. This automates
that look.

Checks:
  1. QEMU VM inventory:    `qm list` on each Proxmox node vs. AGENT.md's table
  2. Orphaned services:    `/opt/services/*` on each docker host vs. the
                            services/<tier>/<service>/ directories in git
  3. Container drift:      actual `docker ps` on each docker host vs. the one
                            service that host's inventory entry says it runs.
                            Catches deploys that bypass /opt/services entirely
                            (e.g. Portainer's own "git repository" stacks);
                            see docusaurus/docs/coe/2026-07-14-portainer-stray-git-stack.md.
                            Also flags any node-exporter container outside the
                            shared `node-exporter` compose project (one inside
                            `caddy` held port 9100 for ~3 months, 2026-10).
  4. node_exporter lint:   no service compose file re-introduces the
                            per-service node_exporter block that was
                            centralized into services/_shared/node-exporter/
  5. Jump host access:     every LXC's root authorized_keys vs. the jump
                            host's pubkey (ansible/playbooks/authorize-jump.yml),
                            so a newly scaffolded LXC that never got the
                            playbook run against it gets caught instead of
                            silently breaking the one-hop `-J` guarantee.
  6. MOTD disabled:        every LXC's /etc/pam.d/sshd vs. an active
                            pam_motd.so line (ansible/playbooks/disable-motd.yml),
                            same gap: a fresh LXC ships with the template
                            default (MOTD on) until someone re-runs it.

Read-only: never modifies anything on a remote host. Posts a summary to ntfy
if reachable; always prints the same summary to stdout.

Usage:
  python3 scripts/audit_infra.py                 # run all checks, post to ntfy
  python3 scripts/audit_infra.py --no-ntfy        # print only, skip the POST
  python3 scripts/audit_infra.py --check vms      # run one check (vms|orphans|container-drift|node-exporter|jump-access|motd-disabled)
"""
import argparse
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENT_MD = ROOT / "AGENT.md"
SERVICES_DIR = ROOT / "services"
INVENTORY = ROOT / "ansible/inventory/hosts.yml"
AUTHORIZE_JUMP_PLAYBOOK = ROOT / "ansible/playbooks/authorize-jump.yml"
NTFY_URL = "http://10.0.1.21/homelab"

PROXMOX_NODES = {
    "node1": "10.0.0.10",
    "node2": "10.0.0.11",
    "node3": "10.0.0.12",
}

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new"]


def _ssh(host, cmd, user="root"):
    """Run a read-only command over SSH. Returns stdout, or None if unreachable."""
    try:
        result = subprocess.run(
            ["ssh"] + SSH_OPTS + [f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_vm_inventory():
    """Diff live `qm list` output against AGENT.md's QEMU VM inventory table."""
    problems = []

    # Parse AGENT.md's table: | VMID | Name | Node | Status | Notes |
    text = AGENT_MD.read_text()
    table_match = re.search(r"## Current QEMU VM inventory\n\n(.*?)\n\n", text, re.S)
    documented = {}
    if table_match:
        for line in table_match.group(1).splitlines()[2:]:  # skip header + separator
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            vmid, name, node, status = cells[0], cells[1], cells[2], cells[3]
            if vmid.isdigit():
                documented[vmid] = {"name": name, "node": node, "status": status}

    live = {}
    for node, ip in PROXMOX_NODES.items():
        out = _ssh(ip, "qm list")
        if out is None:
            problems.append(f"UNREACHABLE: {node} ({ip}); skipped, can't verify its VMs")
            continue
        for line in out.splitlines()[1:]:  # skip header
            parts = line.split()
            if len(parts) < 3:
                continue
            vmid, name, status = parts[0], parts[1], parts[2].lower()
            live[vmid] = {"name": name, "node": node, "status": status}

    for vmid, doc in documented.items():
        if vmid not in live:
            problems.append(
                f"VM {vmid} ({doc['name']}) is documented in AGENT.md as on "
                f"{doc['node']} but does not exist on any reachable node")
        else:
            actual = live[vmid]
            if actual["node"] != doc["node"]:
                problems.append(
                    f"VM {vmid} ({doc['name']}): AGENT.md says node={doc['node']}, "
                    f"actually on {actual['node']}")
            doc_status = doc["status"].lower()
            if doc_status in ("running", "stopped") and doc_status != actual["status"]:
                problems.append(
                    f"VM {vmid} ({doc['name']}): AGENT.md says status={doc['status']}, "
                    f"actually {actual['status']}")

    for vmid, actual in live.items():
        if vmid not in documented:
            problems.append(
                f"VM {vmid} ({actual['name']}) on {actual['node']} exists but is "
                f"not in AGENT.md's QEMU VM inventory table")

    return problems


# Directories under /opt/services/ that are real, git-tracked deployments but
# don't follow the standard services/<tier>/<service>/ one-directory-per-name
# layout, so the plain directory-name diff below would otherwise flag them:
#   node-exporter    -> services/_shared/node-exporter/ (playbooks/node-exporter.yml)
#   portainer-agent  -> services/core/portainer/agent-compose.yml (a sibling file,
#                       not its own directory), via ansible/roles/portainer-agent/
#   docs             -> the whole docusaurus/ dir rsynced + built, via
#                       playbooks/docs.yml; not a services/<tier>/docs/ stack
KNOWN_SPECIAL_DEPLOYS = {"node-exporter", "portainer-agent", "docs"}

# Hosts whose whole job is running an arbitrary, changing set of
# sub-deployments (a PaaS, an orchestrator); "one host = one compose
# project" doesn't hold for these, so check_running_container_drift skips
# them entirely rather than false-positiving on every app deployed through
# the platform.
CONTAINER_DRIFT_EXEMPT_HOSTS = {"coolify", "appdev00"}  # appdev00 = Coolify remote server


def check_orphaned_services():
    """Diff /opt/services/* on each docker host against services/<tier>/<svc>/ in git."""
    problems = []
    inv = yaml.safe_load(INVENTORY.read_text())
    docker_hosts = inv["all"]["children"]["docker_hosts"]["children"]

    git_services = {p.name for p in SERVICES_DIR.glob("*/*") if p.is_dir()}

    for tier_name, tier in docker_hosts.items():
        for host_name, host_vars in (tier.get("hosts") or {}).items():
            ip = host_vars.get("ansible_host")
            ssh_user = host_vars.get("ansible_user", "root")
            if not ip:
                continue
            out = _ssh(ip, "find /opt/services -mindepth 1 -maxdepth 1 -type d -printf '%f\\n' 2>/dev/null", user=ssh_user)
            if out is None:
                problems.append(f"UNREACHABLE: {host_name} ({ip}); skipped, can't check for orphaned stacks")
                continue
            deployed = {d for d in out.splitlines() if d}
            for d in deployed:
                if d not in git_services and d not in KNOWN_SPECIAL_DEPLOYS:
                    problems.append(
                        f"ORPHAN: {host_name} ({ip}) runs /opt/services/{d}; "
                        f"no matching services/*/{d}/ directory in git")
    return problems


def check_running_container_drift():
    """Diff *actually running* containers on each docker host against the one
    service that host is supposed to run per inventory.

    check_orphaned_services() only looks at /opt/services/* directory names,
    it never inspects `docker ps`. That gap is exactly what let a Portainer
    "git repository" stack (2026-07, incident writeup in
    docusaurus/docs/coe/2026-07-14-portainer-stray-git-stack.md) deploy
    duplicate Authentik/Tailscale/Vaultwarden containers straight onto the
    portainer host, invisibly, for ~2 months, they never touched
    /opt/services so the existing check had nothing to diff against. This
    checks the thing that actually matters: what's running, not what's on
    disk in the one path we expect deploys to use.
    """
    problems = []
    inv = yaml.safe_load(INVENTORY.read_text())
    docker_hosts = inv["all"]["children"]["docker_hosts"]["children"]

    for tier_name, tier in docker_hosts.items():
        for host_name, host_vars in (tier.get("hosts") or {}).items():
            ip = host_vars.get("ansible_host")
            ssh_user = host_vars.get("ansible_user", "root")
            expected_service = host_vars.get("service", host_name)
            if not ip or host_name in CONTAINER_DRIFT_EXEMPT_HOSTS:
                continue
            out = _ssh(
                ip,
                r"""docker ps --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Image}}'""",
                user=ssh_user,
            )
            if out is None:
                # Already reported as unreachable by check_orphaned_services;
                # don't double-report here.
                continue
            for line in out.splitlines():
                if not line.strip() or "\t" not in line:
                    continue
                name, project, *rest = line.split("\t")
                project = project.strip()
                image = rest[0].strip() if rest else ""
                # The DRIFT check below passes a node_exporter whose project is this
                # host's own service or "node-exporter" (in KNOWN_SPECIAL_DEPLOYS).
                # Only the shared stack (playbooks/node-exporter.yml) should run
                # one; a second copy fights it for host port 9100. In 2026-10 an
                # orphaned caddy-node-exporter-1 (project 'caddy') held the port for
                # ~3 months while the shared one crash-looped, and nothing flagged it.
                is_node_exporter = "node-exporter" in name or image.startswith("prom/node-exporter")
                if is_node_exporter and project != "node-exporter":
                    problems.append(
                        f"STRAY NODE_EXPORTER: {host_name} ({ip}) runs node-exporter container "
                        f"'{name}' (image '{image}') in compose project '{project or 'none'}', "
                        f"not the shared 'node-exporter' project; it can hold host port 9100 "
                        f"and crash-loop the shared stack. Remove it and re-run "
                        f"playbooks/node-exporter.yml")
                    continue
                if not project:
                    problems.append(
                        f"UNLABELED: {host_name} ({ip}) runs container '{name}' with no "
                        f"com.docker.compose.project label; can't verify it belongs here")
                    continue
                if project != expected_service and project not in KNOWN_SPECIAL_DEPLOYS:
                    problems.append(
                        f"DRIFT: {host_name} ({ip}) is running compose project "
                        f"'{project}' (container '{name}') but this host's inventory "
                        f"service is '{expected_service}'; likely deployed outside "
                        f"the tracked ansible flow (e.g. via Portainer stacks)")
    return problems


def check_node_exporter_regression():
    """Fail if any service compose file re-introduces node_exporter (should be centralized)."""
    problems = []
    for compose_file in SERVICES_DIR.glob("*/*/docker-compose.yml"):
        if "_shared/node-exporter" in str(compose_file):
            continue
        text = compose_file.read_text()
        if re.search(r"^\s*node-exporter:", text, re.M):
            rel = compose_file.relative_to(ROOT)
            problems.append(
                f"REGRESSION: {rel} has its own node-exporter: block again; "
                f"should use services/_shared/node-exporter/ via playbooks/node-exporter.yml")
    return problems


def _all_lxc_hosts():
    """Every LXC in the inventory: docker_hosts (core/prod/test) + runners.
    Excludes docker_hosts' nested `gateways` subgroup (raspberrypi: Pi
    hardware, not an LXC, non-root ansible_user) and everything outside
    docker_hosts/runners (proxmox_nodes, legacy_vms, desktop_vms, bastions).
    Shared by every check that needs to SSH into "every LXC".
    """
    inv = yaml.safe_load(INVENTORY.read_text())
    children = inv["all"]["children"]
    hosts = {}
    for tier_name, tier in children["docker_hosts"]["children"].items():
        if tier_name == "gateways":
            continue
        hosts.update(tier.get("hosts") or {})
    hosts.update(children["runners"]["hosts"])
    return hosts


def check_jump_key_authorized():
    """Verify every non-bastion LXC has the jump host's pubkey in root's
    authorized_keys, so `ssh -J root@jump.example.com root@<host>`
    (docusaurus/docs/stack/jump.md) keeps working for every host.

    authorize-jump.yml only runs when someone remembers to invoke it by
    hand after provisioning a new LXC; this is what catches it when they
    don't, the same way check_orphaned_services catches a forgotten deploy.
    """
    problems = []

    text = AUTHORIZE_JUMP_PLAYBOOK.read_text()
    m = re.search(r'jump_pubkey:\s*"([^"]+)"', text)
    if not m:
        problems.append(
            f"could not parse jump_pubkey out of {AUTHORIZE_JUMP_PLAYBOOK.relative_to(ROOT)}")
        return problems
    pubkey = m.group(1)

    for host_name, host_vars in _all_lxc_hosts().items():
        ip = host_vars.get("ansible_host")
        ssh_user = host_vars.get("ansible_user", "root")
        if not ip:
            continue
        out = _ssh(ip, "cat /root/.ssh/authorized_keys 2>/dev/null", user=ssh_user)
        if out is None:
            problems.append(f"UNREACHABLE: {host_name} ({ip}); skipped, can't verify jump access")
            continue
        if pubkey not in out:
            problems.append(
                f"NO-JUMP-ACCESS: {host_name} ({ip}) is missing the jump host's key in "
                f"authorized_keys; run `ansible-playbook playbooks/authorize-jump.yml`")
    return problems


def check_motd_disabled():
    """Verify no LXC has an active (uncommented) pam_motd.so line in
    /etc/pam.d/sshd; a freshly scaffolded LXC ships with the Debian
    template default (MOTD on), and disable-motd.yml only runs when someone
    remembers to invoke it by hand. Same self-healing role as jump-access.
    """
    problems = []

    for host_name, host_vars in _all_lxc_hosts().items():
        ip = host_vars.get("ansible_host")
        ssh_user = host_vars.get("ansible_user", "root")
        if not ip:
            continue
        out = _ssh(ip, "grep -c '^session.*pam_motd' /etc/pam.d/sshd 2>/dev/null", user=ssh_user)
        if out is None:
            problems.append(f"UNREACHABLE: {host_name} ({ip}); skipped, can't verify motd status")
            continue
        if out.strip() != "0":
            problems.append(
                f"MOTD-ENABLED: {host_name} ({ip}) still has an active pam_motd.so line in "
                f"/etc/pam.d/sshd; run `ansible-playbook playbooks/disable-motd.yml`")
    return problems


CHECKS = {
    "vms": ("QEMU VM inventory", check_vm_inventory),
    "orphans": ("Orphaned services", check_orphaned_services),
    "container-drift": ("Running container drift", check_running_container_drift),
    "node-exporter": ("node_exporter regression", check_node_exporter_regression),
    "jump-access": ("Jump host SSH access", check_jump_key_authorized),
    "motd-disabled": ("MOTD disabled", check_motd_disabled),
}


def post_to_ntfy(summary, username=None, password=None):
    """Best-effort notification: the ntfy topic requires auth (deny-all default).
    Pass --ntfy-username/--ntfy-password, or NTFY_USERNAME/NTFY_PASSWORD env vars."""
    try:
        import base64
        import urllib.request
        headers = {"Title": "Homelab infra audit", "Priority": "default"}
        if username and password:
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        req = urllib.request.Request(NTFY_URL, data=summary.encode(), method="POST", headers=headers)
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as exc:  # noqa: BLE001 (best-effort notification, never fatal)
        print(f"(ntfy post failed: {exc})", file=sys.stderr)
        return False


def main():
    import os

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", choices=CHECKS.keys(), help="run only this check")
    ap.add_argument("--no-ntfy", action="store_true", help="don't post to ntfy, print only")
    ap.add_argument("--ntfy-username", default=os.environ.get("NTFY_USERNAME"))
    ap.add_argument("--ntfy-password", default=os.environ.get("NTFY_PASSWORD"))
    args = ap.parse_args()

    checks_to_run = {args.check: CHECKS[args.check]} if args.check else CHECKS
    all_problems = []
    lines = ["Homelab infra audit"]

    for key, (label, fn) in checks_to_run.items():
        problems = fn()
        all_problems.extend(problems)
        lines.append(f"\n{label}: {len(problems)} issue(s)")
        for p in problems:
            lines.append(f"  - {p}")

    summary = "\n".join(lines)
    print(summary)

    if not all_problems:
        print("\nno drift detected")
    elif not args.no_ntfy:
        post_to_ntfy(summary, args.ntfy_username, args.ntfy_password)

    sys.exit(1 if all_problems else 0)


if __name__ == "__main__":
    main()
