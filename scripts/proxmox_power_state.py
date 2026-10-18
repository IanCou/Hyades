#!/usr/bin/env python3
"""Write an Ansible inventory fragment that puts powered-off guests in `stopped`.

CI's deploy job runs every playbook with `!ci_deploy_skip`, and `stopped` is a
child of that group. Hand-maintaining that list drifts the same way the old
static prometheus.yml did, so the deploy job asks Proxmox instead: this script
reads `pvesh get /cluster/resources --type vm` over SSH (same root SSH path
audit_infra.py uses, no API token on the runner) and emits every inventory host
whose Proxmox guest of the same name is not running.

Any one quorate node answers for the whole cluster, so nodes are tried in
order. If none answers, the script exits 1 and the deploy job fails before
touching any host: deploying blind would put powered-off guests back on the
UNREACHABLE path that broke run 39100257683.

Hosts with no Proxmox guest of the same name (the Pi) are left alone; they
are never added to `stopped`.

Usage (from ansible/):
  python3 ../scripts/proxmox_power_state.py inventory/hosts.yml "$RUNNER_TEMP/proxmox-state.yml"
  export ANSIBLE_INVENTORY="inventory/hosts.yml,$RUNNER_TEMP/proxmox-state.yml"
"""
import json
import os
import shutil
import subprocess
import sys

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new"]
PVESH = "pvesh get /cluster/resources --type vm --output-format json"


def ansible_inventory_bin():
    # The runner's github-runner role symlinked only some venv binaries into
    # /usr/local/bin, so ansible-inventory was missing from PATH there (run
    # 39160219243). Fall back to the venv that ansible-playbook resolves to.
    found = shutil.which("ansible-inventory")
    if found:
        return found
    playbook = shutil.which("ansible-playbook")
    if playbook:
        sibling = os.path.join(os.path.dirname(os.path.realpath(playbook)), "ansible-inventory")
        if os.access(sibling, os.X_OK):
            return sibling
    sys.exit("::error::ansible-inventory not found on PATH or next to ansible-playbook")


def inventory(path):
    out = subprocess.run(
        [ansible_inventory_bin(), "-i", path, "--list"],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    hostvars = data["_meta"]["hostvars"]
    nodes = [hostvars[h]["ansible_host"] for h in data["proxmox_nodes"]["hosts"]]
    return set(hostvars), nodes


def cluster_guests(nodes):
    for ip in nodes:
        try:
            result = subprocess.run(
                ["ssh"] + SSH_OPTS + [f"root@{ip}", PVESH],
                capture_output=True, text=True, timeout=20,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"proxmox {ip}: {exc}", file=sys.stderr)
            continue
        if result.returncode != 0:
            print(f"proxmox {ip}: rc={result.returncode} {result.stderr.strip()}", file=sys.stderr)
            continue
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            print(f"proxmox {ip}: bad JSON: {exc}", file=sys.stderr)
    return None


def should_skip(guest):
    """Return True if CI must not deploy to this Proxmox guest."""
    # Templates are never deployable. "stopped" and "paused" are deliberate
    # power states. "unknown" (its node dropped out of the cluster) is NOT
    # skipped: the deploy then fails on it, so a dead node turns the job red
    # instead of hiding behind a green skip.
    if guest.get("template") == 1:
        return True
    return guest.get("status") in ("stopped", "paused")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    inventory_path, out_path = sys.argv[1], sys.argv[2]

    hosts, nodes = inventory(inventory_path)
    guests = cluster_guests(nodes)
    if guests is None:
        print("::error::no Proxmox node answered pvesh; refusing to deploy blind")
        sys.exit(1)

    stopped = sorted(
        g["name"] for g in guests
        if g.get("type") in ("lxc", "qemu") and g.get("name") in hosts and should_skip(g)
    )

    # JSON is valid YAML; Ansible's yaml inventory plugin reads it as-is.
    fragment = {"all": {"children": {"stopped": {"hosts": {h: {} for h in stopped}}}}}
    with open(out_path, "w") as f:
        json.dump(fragment, f, indent=2)

    print(f"stopped (from Proxmox): {', '.join(stopped) or 'none'}")


if __name__ == "__main__":
    main()
