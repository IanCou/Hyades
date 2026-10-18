#!/usr/bin/env python3
"""Scaffold every file a new homelab service needs.

Stamps a terraform module, an Ansible inventory row, a compose stack,
a Caddy reverse-proxy block, and a Docusaurus stack page, then regenerates
network.md. Picks the next free LXC id and IP for the tier so it never
collides with an existing one.

Usage:
  python3 scripts/new_service.py <name> <tier> <node>
    name  service name, e.g. "vaultwarden"
    tier  core | prod | test
    node  Proxmox node, e.g. "node1"
"""
import re
import sys
import pathlib

sys.dont_write_bytecode = True  # don't leave a scripts/__pycache__ behind
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_docs  # noqa: E402  (local import after sys.path tweak)

ROOT = gen_docs.ROOT
PLACEHOLDER_PORT = 8080

# tier -> (/24 third octet, lowest LXC id in the range)
TIERS = {
    "core": (1, 111),
    "prod": (2, 211),
    "test": (3, 601),
}


def die(msg):
    sys.exit(f"error: {msg}")


def tf_module_name(name):
    """Terraform module label: hyphens are illegal, so use underscores."""
    return name.replace("-", "_")


def next_ids(tier):
    """Return (vm_id, ip) one past the highest existing in the tier."""
    third, base_id = TIERS[tier]
    rows = gen_docs.parse_tf(tier)
    vm_id = max([r["vm"] for r in rows], default=base_id - 1) + 1
    last_octets = [int(r["ip"].rsplit(".", 1)[-1]) for r in rows
                   if r["ip"].startswith(f"10.0.{third}.")]
    octet = max(last_octets, default=9) + 1
    return vm_id, f"10.0.{third}.{octet}"


def ensure_absent(name, tier):
    """Exit if the service already exists anywhere we'd write it."""
    tf_text = (ROOT / f"terraform/envs/{tier}/main.tf").read_text()
    if re.search(rf'module\s+"{re.escape(tf_module_name(name))}"\s*\{{', tf_text):
        die(f"terraform module '{name}' already exists in {tier}/main.tf")

    inv_text = (gen_docs.INVENTORY).read_text()
    if re.search(rf"^\s*service:\s*{re.escape(name)}\s*$", inv_text, re.M):
        die(f"inventory already has a service named '{name}'")

    if (ROOT / f"services/{tier}/{name}").exists():
        die(f"services/{tier}/{name} already exists")


def stamp_terraform(name, tier, node, vm_id, ip):
    path = ROOT / f"terraform/envs/{tier}/main.tf"
    text = path.read_text()
    block = f'''
module "{tf_module_name(name)}" {{
  source = "../../modules/lxc-docker"

  node_name        = "{node}"
  vm_id            = {vm_id}
  hostname         = "{name}"
  ip_address       = "{ip}/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["{tier}", "docker"]
}}
'''
    path.write_text(text.rstrip("\n") + "\n" + block)


def stamp_inventory(name, tier, node, vm_id, ip):
    path = gen_docs.INVENTORY
    lines = path.read_text().splitlines(keepends=True)

    # Find the `<tier>:` host group, then the end of its hosts: block.
    tier_re = re.compile(rf"^(\s*){tier}:\s*$")
    start = None
    indent = ""
    for i, line in enumerate(lines):
        m = tier_re.match(line)
        if m and i + 1 < len(lines) and "hosts:" in lines[i + 1]:
            start = i + 2  # first host row under `hosts:`
            indent = m.group(1) + "    "  # host rows are tier-indent + 4
            break
    if start is None:
        die(f"could not find inventory group '{tier}:' with a hosts: block")

    # Walk forward while we're still inside this group's host rows, tracking
    # the last non-blank in-group line so we insert right after it (and leave
    # any trailing blank line as the separator before the next group).
    end = start
    cur = start
    while cur < len(lines):
        stripped = lines[cur].rstrip("\n")
        if stripped and not stripped.startswith(indent):
            break
        cur += 1
        if stripped:
            end = cur

    row = (
        f"{indent}{name}:\n"
        f"{indent}  ansible_host: {ip} # LXC {vm_id}\n"
        f"{indent}  service: {name}\n"
        f"{indent}  tier: {tier}\n"
    )
    lines[end:end] = [row]
    path.write_text("".join(lines))


def stamp_service_dir(name, tier):
    svc_dir = ROOT / f"services/{tier}/{name}"
    svc_dir.mkdir(parents=True, exist_ok=True)
    (svc_dir / "docker-compose.yml").write_text(f'''services:
  {name}:
    image: # TODO: set image
    container_name: {name}
    restart: unless-stopped
    ports:
      - "{PLACEHOLDER_PORT}:{PLACEHOLDER_PORT}"
    environment:
      - TZ=${{GENERIC_TIMEZONE}}
    volumes:
      - ./data:/data
''')
    (svc_dir / ".env.example").write_text(
        "SUBDOMAIN=\nDOMAIN_NAME=\nGENERIC_TIMEZONE=\n"
    )


def stamp_caddy(name, ip):
    path = gen_docs.CADDYFILE
    block = (
        f"\n{name}.example.com {{\n"
        f"\treverse_proxy {ip}:{PLACEHOLDER_PORT}\n"
        f"}}\n"
    )
    path.write_text(path.read_text().rstrip("\n") + "\n" + block)


def stamp_stack_page(name, tier, vm_id, node, ip):
    path = gen_docs.STACK_DIR / f"{name}.md"
    path.write_text(f'''---
title: {name}
sidebar_position: 99
---

# {name}

TODO: describe what {name} does.

|        |                                              |
| ------ | -------------------------------------------- |
| LXC    | {vm_id} on {node}                            |
| IP     | {ip}                                |
| Port   | `:{PLACEHOLDER_PORT}`                         |
| URL    | `https://{name}.example.com`             |
| Deploy | standard `deploy.yml`                        |

## Configuration

Runtime config comes from `.env` (see [`services/{tier}/{name}/.env.example`](https://github.com/IanCou/Hyades/blob/main/services/{tier}/{name}/.env.example)).
''')


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: python3 scripts/new_service.py <name> <tier> <node>")
    name, tier, node = sys.argv[1], sys.argv[2], sys.argv[3]

    if tier not in TIERS:
        die(f"tier must be one of {', '.join(TIERS)}, got '{tier}'")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        die(f"name must be lowercase alphanumeric/hyphen, got '{name}'")

    ensure_absent(name, tier)
    vm_id, ip = next_ids(tier)

    stamp_terraform(name, tier, node, vm_id, ip)
    stamp_inventory(name, tier, node, vm_id, ip)
    stamp_service_dir(name, tier)
    stamp_caddy(name, ip)
    stamp_stack_page(name, tier, vm_id, node, ip)

    # Regenerate the machine-derived tables in network.md.
    gen_docs.NETWORK_MD.write_text(gen_docs.build())

    print(f"scaffolded '{name}' in {tier}: LXC {vm_id} @ {ip} on {node}")
    print("  terraform/envs/%s/main.tf" % tier)
    print("  ansible/inventory/hosts.yml")
    print(f"  services/{tier}/{name}/")
    print("  services/core/caddy/Caddyfile")
    print(f"  docusaurus/docs/stack/{name}.md")
    print("  docusaurus/docs/network.md (regenerated)")
    print()
    print(f"REMINDER: add the AdGuard DNS rewrite for "
          f"{name}.example.internal using the ansible playbook.")


if __name__ == "__main__":
    main()
