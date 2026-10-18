#!/usr/bin/env python3
"""Generate the machine-derived tables in docusaurus/docs/network.md.

Source of truth (never hand-edit the generated blocks):
  terraform/envs/{core,prod,test}/main.tf  -> LXC inventory tables
  services/core/caddy/Caddyfile            -> reverse-proxy table

Editorial role text lives in ROLES below. Everything else in network.md
(prose, the Infrastructure/Gateway tables, DNS, certs) is hand-written.

Usage:
  python3 scripts/gen_docs.py          # rewrite generated blocks in place
  python3 scripts/gen_docs.py --check  # exit 1 if a rewrite would change anything,
                                       # or if a deployed service has no stack page
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
NETWORK_MD = ROOT / "docusaurus/docs/network.md"
CADDYFILE = ROOT / "services/core/caddy/Caddyfile"
INVENTORY = ROOT / "ansible/inventory/hosts.yml"
STACK_DIR = ROOT / "docusaurus/docs/stack"
# inventory service name -> stack page basename, where they differ
PAGE_ALIASES = {"docs": "docs-site", "appdev00": "peopleportal-staging"}

ROLES = {
    "caddy": "Reverse proxy", "authentik": "SSO", "portainer": "Docker UI",
    "github-runner": "CI/CD", "semaphore": "Ansible UI",
    "tailscale": "VPN + subnet router", "adguard": "DNS", "docs": "Docs site",
    "prometheus": "Metrics", "grafana": "Dashboards",
    "uptime-kuma": "Uptime monitoring", "ntfy": "Push notifications",
    "jump": "SSH bastion (LAN-only)", "speedtest": "Speedtest tracker",
    "immich": "Photos", "nextcloud": "Files", "coolify": "Deployment platform",
    "searxng": "Metasearch",
    "n8n": "Automation", "internship-watcher": "Job scraper",
    "kafka": "Event streaming", "openclaw": "AI gateway (Claude)",
    "dev": "Personal dev box (Docker + Claude Code)",
    "cobalt": "Media downloader (cobalt.tools)",
    "appdev00": "People Portal staging (Coolify remote)",
}

# A module call ends at a `}` in the first column; inner braces are indented.
MODULE_RE = re.compile(r'module\s+"[^"]+"\s*\{(.*?)\n\}', re.S)


def _attr(block, name):
    m = re.search(rf'\n\s*{name}\s*=\s*"?([^"\n#]+?)"?\s*(?:#.*)?$', block, re.M)
    return m.group(1).strip() if m else None


def parse_tf(env):
    text = (ROOT / f"terraform/envs/{env}/main.tf").read_text()
    rows = []
    for m in MODULE_RE.finditer(text):
        b = m.group(1)
        vm, host, node, ip, ipv6 = (_attr(b, k) for k in
                                    ("vm_id", "hostname", "node_name",
                                     "ip_address", "ipv6_address"))
        if not (vm and host and ip):
            continue  # not an lxc-docker module
        rows.append({"vm": int(vm), "host": host, "node": node,
                     "ip": ip.split("/")[0],
                     "ipv6": ipv6.split("/")[0] if ipv6 else None})
    return sorted(rows, key=lambda r: r["vm"])


def parse_caddy():
    routes, cur = {}, []
    for line in CADDYFILE.read_text().splitlines():
        s = line.strip()
        if s.startswith("reverse_proxy") and cur:
            tgt = s.split()[1].replace("https://", "").replace("http://", "")
            for sub in cur:
                routes.setdefault(sub, tgt)
            cur = []  # first reverse_proxy per site block wins
        elif s.endswith("{"):
            cur = [lab.replace("http://", "").replace("https://", "")
                   .removesuffix(".example.com")
                   for lab in s[:-1].split()
                   if lab.replace("http://", "").replace("https://", "")
                   .endswith(".example.com")]

    def sort_key(item):
        sub, tgt = item
        host, _, port = tgt.partition(":")
        try:
            octets = tuple(int(o) for o in host.split("."))
        except ValueError:
            octets = (999,)
        return (octets, int(port) if port.isdigit() else 0, sub)

    return sorted(routes.items(), key=sort_key)


def lxc_table(rows):
    multinode = len({r["node"] for r in rows}) > 1
    octet = lambda r: "." + r["ip"].rsplit(".", 1)[-1]
    role = lambda r: ROLES.get(r["host"], "")
    if multinode:
        out = ["| IP | Host | LXC | Node | Role |", "|----|------|-----|------|------|"]
        out += [f"| {octet(r)} | {r['host']} | {r['vm']} | {r['node']} | {role(r)} |"
                for r in rows]
    else:
        out = ["| IP | Host | LXC | Role |", "|----|------|-----|------|"]
        out += [f"| {octet(r)} | {r['host']} | {r['vm']} | {role(r)} |" for r in rows]
    return "\n".join(out)


def rp_table(routes):
    return "\n".join(["| Subdomain | Backend |", "|-----------|---------|"] +
                     [f"| {sub} | {tgt} |" for sub, tgt in routes])


def _replace(text, block_id, content):
    begin = f"<!-- BEGIN GENERATED: {block_id} -->"
    end = f"<!-- END GENERATED: {block_id} -->"
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    new, n = pat.subn(lambda _: f"{begin}\n{content}\n{end}", text)
    if n == 0:
        sys.exit(f"error: marker '{block_id}' not found in {NETWORK_MD}")
    return new


def build():
    text = NETWORK_MD.read_text()
    text = _replace(text, "lxc-core", lxc_table(parse_tf("core")))
    text = _replace(text, "lxc-prod", lxc_table(parse_tf("prod")))
    text = _replace(text, "lxc-test", lxc_table(parse_tf("test")))
    text = _replace(text, "reverse-proxy", rp_table(parse_caddy()))
    return text


def missing_stack_pages():
    """Inventory services that have no docusaurus/docs/stack/<svc>.md page."""
    services = sorted(set(re.findall(r"^\s*service:\s*(\S+)", INVENTORY.read_text(), re.M)))
    missing = []
    for svc in services:
        page = STACK_DIR / f"{PAGE_ALIASES.get(svc, svc)}.md"
        if not page.exists():
            missing.append(svc)
    return missing


def main():
    new = build()
    if "--check" in sys.argv:
        problems = []
        if new != NETWORK_MD.read_text():
            problems.append("network.md is stale: run `make docs` and commit")
        missing = missing_stack_pages()
        if missing:
            problems.append("missing stack pages for: " + ", ".join(missing))
        if problems:
            sys.exit("\n".join(problems))
        print("docs up to date; every service has a stack page")
    else:
        NETWORK_MD.write_text(new)
        print(f"wrote {NETWORK_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
