#!/usr/bin/env python3
"""
Idempotent Uptime Kuma monitor + notification setup.
Usage: UPTIME_KUMA_USERNAME=<user> UPTIME_KUMA_PASSWORD=<pass> \\
       NTFY_USERNAME=<user> NTFY_PASSWORD=<pass> \\
       python3 setup_monitors.py --url http://10.0.1.20:3001

Public-tunnel services are monitored via their public HTTPS URL.
Internal-only services are monitored via direct LXC IP:port so the uptime-kuma
LXC does not need AdGuard DNS to resolve *.example.com internally.

IPs below come from scripts/gen_docs.py's Terraform parser rather than being
hardcoded a second time; an IP change in terraform/envs/ now propagates here
automatically instead of silently going stale. Ports, health-check paths,
monitor type, and which services get a public tunnel aren't in Terraform and
stay explicit here.
"""
import argparse
import os
import pathlib
import sys

from uptime_kuma_api import UptimeKumaApi, MonitorType, NotificationType

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import gen_docs  # noqa: E402

# Devices with no Terraform module.
_EXTRA_HOSTS = {
    "node1": "10.0.0.10",
    "node2": "10.0.0.11",
    "node3": "10.0.0.12",
    "nas": "10.0.0.249",
}


def _ips():
    ips = dict(_EXTRA_HOSTS)
    for tier in ("core", "prod", "test"):
        for row in gen_docs.parse_tf(tier):
            ips[row["host"]] = row["ip"]
    return ips


IPS = _ips()

MONITORS = [
    # --- External via Cloudflare tunnel (public DNS resolves these) ---
    {"type": MonitorType.HTTP, "name": "Authentik",    "url": "https://auth.example.com"},
    {"type": MonitorType.HTTP, "name": "Immich",       "url": "https://immich.example.com"},
    {"type": MonitorType.HTTP, "name": "Nextcloud",    "url": "https://nextcloud.example.com"},

    # --- Public personal site ---
    {"type": MonitorType.HTTP, "name": "Personal website", "url": "https://www.example.com"},

    # --- Internal only: direct LXC IP:port ---
    {"type": MonitorType.HTTP, "name": "Caddy",        "url": f"http://{IPS['caddy']}"},
    {"type": MonitorType.HTTP, "name": "Portainer",    "url": f"https://{IPS['portainer']}:9443", "ignoreTls": True},
    {"type": MonitorType.HTTP, "name": "AdGuard",      "url": f"http://{IPS['adguard']}:80"},
    {"type": MonitorType.HTTP, "name": "Docs",         "url": f"http://{IPS['docs']}:80"},
    {"type": MonitorType.HTTP, "name": "Uptime Kuma",  "url": f"http://{IPS['uptime-kuma']}:3001"},
    {"type": MonitorType.HTTP, "name": "Grafana",      "url": f"http://{IPS['grafana']}:3000"},
    {"type": MonitorType.HTTP, "name": "Semaphore",    "url": f"http://{IPS['semaphore']}:3000"},
    {"type": MonitorType.HTTP, "name": "Prometheus",   "url": f"http://{IPS['prometheus']}:9090/-/ready"},
    {"type": MonitorType.HTTP, "name": "Ntfy",         "url": f"http://{IPS['ntfy']}:80/healthz"},
    {"type": MonitorType.HTTP, "name": "Coolify",      "url": f"http://{IPS['coolify']}:8000"},
    {"type": MonitorType.HTTP, "name": "n8n",          "url": f"http://{IPS['n8n']}:5678"},
    {"type": MonitorType.HTTP, "name": "Kafka UI",     "url": f"http://{IPS['kafka']}:8080"},
    {"type": MonitorType.HTTP, "name": "SearXNG",      "url": f"http://{IPS['searxng']}:8080"},
    {"type": MonitorType.HTTP, "name": "Speedtest",    "url": f"http://{IPS['speedtest']}:8765"},

    # --- Proxmox UIs: direct IP, self-signed cert ---
    {"type": MonitorType.HTTP, "name": "Proxmox PVE1", "url": f"https://{IPS['node1']}:8006", "ignoreTls": True},
    {"type": MonitorType.HTTP, "name": "Proxmox PVE2", "url": f"https://{IPS['node2']}:8006", "ignoreTls": True},
    {"type": MonitorType.HTTP, "name": "Proxmox PVE3", "url": f"https://{IPS['node3']}:8006", "ignoreTls": True},

    # --- Ping: infrastructure ---
    {"type": MonitorType.PING, "name": "node1",              "hostname": IPS["node1"]},
    {"type": MonitorType.PING, "name": "node2",              "hostname": IPS["node2"]},
    {"type": MonitorType.PING, "name": "node3",              "hostname": IPS["node3"]},
    {"type": MonitorType.PING, "name": "NAS",                "hostname": IPS["nas"]},

    # --- Ping: LXCs without HTTP surface ---
    {"type": MonitorType.PING, "name": "github-runner",      "hostname": IPS["github-runner"]},
    {"type": MonitorType.PING, "name": "tailscale",          "hostname": IPS["tailscale"]},
    {"type": MonitorType.PING, "name": "jump",               "hostname": IPS["jump"]},
    {"type": MonitorType.PING, "name": "internship-watcher", "hostname": IPS["internship-watcher"]},

    # --- TCP port: Kafka broker ---
    {"type": MonitorType.PORT, "name": "Kafka broker",       "hostname": IPS["kafka"], "port": 9092},
]

DEFAULTS = {
    "interval": 60,
    "retryInterval": 60,
    "maxretries": 3,
}

NOTIFICATION_NAME = "Ntfy: homelab"


def setup_notifications(api, ntfy_username, ntfy_password):
    existing = {n["name"]: n for n in api.get_notifications()}
    params = {
        "type": NotificationType.NTFY,
        "name": NOTIFICATION_NAME,
        "isDefault": True,
        "ntfyserverurl": "https://ntfy.example.com",
        "ntfytopic": "homelab",
        "ntfyusername": ntfy_username,
        "ntfypassword": ntfy_password,
        "ntfyPriority": 4,
    }
    current = existing.get(NOTIFICATION_NAME)
    if current is not None:
        if all(current.get(key) == value for key, value in params.items()):
            print(f"  skip   notification '{NOTIFICATION_NAME}'")
            return
        api.edit_notification(current["id"], **params)
        print(f"  update notification '{NOTIFICATION_NAME}'")
        return

    api.add_notification(**params, applyExisting=True)
    print(f"  add    notification '{NOTIFICATION_NAME}' (applied to all monitors)")


def setup_monitors(api):
    existing = {m["name"]: m for m in api.get_monitors()}

    created = updated = skipped = 0
    for spec in MONITORS:
        name = spec["name"]
        params = {**DEFAULTS, **spec}

        if name not in existing:
            api.add_monitor(**params)
            print(f"  add    {name}")
            created += 1
            continue

        current = existing[name]
        current_url = current.get("url", "")
        desired_url = spec.get("url", "")
        if desired_url and current_url != desired_url:
            api.delete_monitor(current["id"])
            api.add_monitor(**params)
            print(f"  update {name}  ({current_url} → {desired_url})")
            updated += 1
        else:
            print(f"  skip   {name}")
            skipped += 1

    print(f"\nMonitors: {created} added, {updated} updated, {skipped} skipped.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",      default="http://10.0.1.20:3001")
    args = parser.parse_args()

    required_vars = (
        "UPTIME_KUMA_USERNAME",
        "UPTIME_KUMA_PASSWORD",
        "NTFY_USERNAME",
        "NTFY_PASSWORD",
    )
    missing = [name for name in required_vars if not os.environ.get(name)]
    if missing:
        parser.error(f"Missing required environment variables: {', '.join(missing)}")

    api = UptimeKumaApi(args.url, wait_events=3)
    api.login(os.environ["UPTIME_KUMA_USERNAME"], os.environ["UPTIME_KUMA_PASSWORD"])

    print("--- Notifications ---")
    setup_notifications(api, os.environ["NTFY_USERNAME"], os.environ["NTFY_PASSWORD"])

    print("\n--- Monitors ---")
    setup_monitors(api)

    api.disconnect()


if __name__ == "__main__":
    main()
