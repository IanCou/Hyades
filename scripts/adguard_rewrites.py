#!/usr/bin/env python3
"""Idempotent AdGuard Home DNS rewrite reconciliation via its REST API.

Replaces hand-editing AdGuardHome.yaml's `rewrites:` list over SSH. Rewrites
are derived from the same source of truth as network.md's generated tables
(scripts/gen_docs.py: Terraform inventory + Caddyfile), so a new service only
needs `make docs` to also get its DNS rewrite; no manual AdGuard edit.

Desired set, one A rewrite plus (where a static IPv6 is configured) one AAAA
rewrite per service:
  <service>.example.internal -> the service's LXC IP(s) (from Terraform)
  <domain>.example.com        -> Caddy's IP(s) (from the Caddyfile, for LAN
                                      clients so *.example.com resolves
                                      internally instead of round-tripping
                                      through public DNS/Cloudflare)
plus a small EXTRA_HOSTS list for devices with no Terraform module (Proxmox
hypervisors themselves).

IPv6 answers are always the static ULA address set in Terraform
(fd00:db8::/64), never a container's SLAAC/RA-derived address
(neither its randomer ULA nor its ISP-delegated public 2600:.../64; those
are dynamic and not something DNS should point at).

A domain can legitimately have more than one answer (an A and a AAAA), so
this reconciles per-domain SETS of answers rather than a single answer per
domain; the earlier single-answer-per-domain model silently discarded
whichever record the AdGuard API happened to list second for a domain, so
a coexisting A+AAAA pair would flap: each run "corrected" the one it kept
track of back to a single family, quietly deleting the other.

This script only ADDS or REMOVES answers for domains in its derived set;
it never touches a domain outside that set (e.g. a manually-added personal
device entry like desktop.example.com is left alone).

Usage:
  ADGUARD_PASSWORD=<pass> python3 scripts/adguard_rewrites.py \
      --url http://10.0.1.16:80 --username <user>
  python3 scripts/adguard_rewrites.py --dry-run ...   # print the plan, no API calls
"""
import argparse
import os
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_docs  # noqa: E402  (sibling module: parse_tf / parse_caddy)

CADDY_IP = "10.0.1.10"
CADDY_IPV6 = "fd00:db8::1:10"

# Devices with no Terraform module: add here, not to the Caddyfile/inventory.
# IPv4-only: no static IPv6 has been assigned to these hosts.
EXTRA_HOSTS = {
    "node1.example.internal": {"10.0.0.10"},
    "node2.example.internal": {"10.0.0.11"},
    "node3.example.internal": {"10.0.0.12"},
    # Ad-hoc QEMU VMs (qm create, not Terraform-managed), see AGENT.md's
    # "Current QEMU VM inventory".
    "windowsvm00.example.internal": {"10.0.0.44"},
    "macosvm00.example.internal": {"10.0.0.45"},
    "archvm00.example.internal": {"10.0.0.46"},
    "ubuntuvm00.example.internal": {"10.0.0.47"},
    "desktop00.example.internal": {"10.0.0.9"},
}


def desired_rewrites():
    out = {domain: set(answers) for domain, answers in EXTRA_HOSTS.items()}
    for tier in ("core", "prod", "test"):
        for row in gen_docs.parse_tf(tier):
            answers = {row["ip"]}
            if row["ipv6"]:
                answers.add(row["ipv6"])
            out[f"{row['host']}.example.internal"] = answers
    for sub, _tgt in gen_docs.parse_caddy():
        out.setdefault(f"{sub}.example.com", set()).update({CADDY_IP, CADDY_IPV6})
    return out


class AdGuardClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        resp = self.session.post(
            f"{self.base_url}/control/login",
            json={"name": username, "password": password},
            timeout=10,
        )
        resp.raise_for_status()

    def list_rewrites(self):
        """domain -> set of answers. A domain may have both an A and AAAA answer."""
        resp = self.session.get(f"{self.base_url}/control/rewrite/list", timeout=10)
        resp.raise_for_status()
        current = {}
        for r in resp.json():
            current.setdefault(r["domain"], set()).add(r["answer"])
        return current

    def add(self, domain, answer):
        resp = self.session.post(
            f"{self.base_url}/control/rewrite/add",
            json={"domain": domain, "answer": answer},
            timeout=10,
        )
        resp.raise_for_status()

    def delete(self, domain, answer):
        resp = self.session.post(
            f"{self.base_url}/control/rewrite/delete",
            json={"domain": domain, "answer": answer},
            timeout=10,
        )
        resp.raise_for_status()


def reconcile(client, desired, dry_run=False):
    current = client.list_rewrites()
    added, removed = [], []

    for domain, answers in sorted(desired.items()):
        have = current.get(domain, set())
        for answer in sorted(answers - have):
            added.append((domain, answer))
            if not dry_run:
                client.add(domain, answer)
        for answer in sorted(have - answers):
            removed.append((domain, answer))
            if not dry_run:
                client.delete(domain, answer)

    untouched_foreign = sorted(set(current) - set(desired))
    return added, removed, untouched_foreign


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True, help="AdGuard Home base URL, e.g. http://10.0.1.16:80")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", help="or set ADGUARD_PASSWORD; avoids the value showing up "
                                        "in argv (process listings, shell history, error traces)")
    ap.add_argument("--dry-run", action="store_true",
                    help="log in and read current state, but skip add/delete calls")
    args = ap.parse_args()

    password = args.password or os.environ.get("ADGUARD_PASSWORD")
    if not password:
        ap.error("--password or ADGUARD_PASSWORD is required")

    desired = desired_rewrites()
    client = AdGuardClient(args.url, args.username, password)
    added, removed, foreign = reconcile(client, desired, dry_run=args.dry_run)

    prefix = "[dry-run] " if args.dry_run else ""
    for d, a in added:
        print(f"{prefix}add: {d} -> {a}")
    for d, a in removed:
        print(f"{prefix}remove: {d} -> {a}")
    print(f"left alone (not in derived set): {len(foreign)} entries "
          f"({', '.join(foreign)})" if foreign else "left alone: 0 entries")
    if not added and not removed:
        print("nothing to do: rewrites already match Terraform + Caddyfile")


if __name__ == "__main__":
    main()
