#!/usr/bin/env python3
"""Fixed public summary of private Prometheus metrics and approved HTTPS checks.

Only the background collector contacts upstreams. HTTP readers get an in-memory,
bounded-age snapshot. No query, URL, label, or error supplied by a reader is used.
"""
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import logging
import math
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = logging.getLogger("public-overview")
PATH = "/v1/overview.json"
METRICS = ("cpuPercent", "memoryPercent", "storagePercent", "availabilityPercent")
REFRESH_SECONDS = 60
MAX_AGE_SECONDS = 300
TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 256 * 1024


def queries(expected_nodes):
    """All resource metrics use host exporters, never container/LXC exporters."""
    up = 'up{job="proxmox"}'
    complete = f'(count({up}) == {expected_nodes}) and (sum({up}) == {expected_nodes})'
    cpu = 'rate(node_cpu_seconds_total{job="proxmox",mode="idle"}[5m])'
    available = 'node_memory_MemAvailable_bytes{job="proxmox"}'
    total = 'node_memory_MemTotal_bytes{job="proxmox"}'
    # One root filesystem per host. This intentionally excludes NAS, local-lvm,
    # guest disks, bind mounts and all Docker/LXC exporter filesystem metrics.
    selector = '{job="proxmox",mountpoint="/",fstype!~"rootfs|tmpfs|overlay"}'
    free = 'node_filesystem_avail_bytes' + selector
    size = 'node_filesystem_size_bytes' + selector
    current_hosts = f'group by (host) ({up})'
    history_by_host = f'avg by (host) (avg_over_time({up}[24h]))'
    current_history = f'({history_by_host}) and on (host) {current_hosts}'
    return {
        "cpuPercent": f'100 * (1 - avg({cpu})) and (count(count by (instance) ({cpu})) == {expected_nodes}) and ({complete})',
        "memoryPercent": f'100 * (1 - sum({available}) / sum({total})) and (count({available}) == {expected_nodes}) and (count({total}) == {expected_nodes}) and ({complete})',
        "storagePercent": f'100 * (1 - sum({free}) / sum({size})) and (count({free}) == {expected_nodes}) and (count({size}) == {expected_nodes}) and ({complete})',
        # Exporter scrape success over observed samples in the last 24 hours.
        # Current host labels exclude retired target IPs from the range. This is
        # not application uptime, and a fresh installation has less history.
        "availabilityPercent": f'100 * avg({current_history}) and (count({current_hosts}) == {expected_nodes}) and (count({current_history}) == {expected_nodes})',
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def prometheus_value(base_url, query):
    url = base_url + "/api/v1/query?" + urllib.parse.urlencode({"query": query, "timeout": "4s"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("oversized upstream response")
    data = json.loads(raw)
    result = data.get("data", {}).get("result", [])
    if data.get("status") != "success" or data.get("data", {}).get("resultType") != "vector" or len(result) != 1:
        raise ValueError("expected one aggregate value")
    # Aggregates must have no host/instance labels; never forward upstream objects.
    if result[0].get("metric"):
        raise ValueError("expected unlabelled aggregate")
    sampled_at, raw_value = result[0]["value"]
    if abs(time.time() - float(sampled_at)) > 30:
        raise ValueError("outdated upstream response")
    value = float(raw_value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("invalid percentage")
    return round(value, 2)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect only to the validated public IP while verifying the original host."""
    def __init__(self, host, address):
        super().__init__(host, port=443, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def public_target(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("checks must use credential-free public HTTPS URLs on port 443")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise ValueError("checks must use public DNS names, not IP literals")
    if "." not in parsed.hostname or any(c in url for c in "\r\n\t"):
        raise ValueError("invalid public hostname")
    return parsed


def probe(url):
    parsed = public_target(url)
    addresses = sorted({info[4][0] for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("probe DNS resolved to a non-public address")
    connection = PinnedHTTPSConnection(parsed.hostname, addresses[0])
    try:
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection.request("GET", path, headers={"User-Agent": "Hyades-Public-Overview/1.0", "Accept": "text/html"})
        response = connection.getresponse()
        # A redirect means the public entry point answered. Never follow it:
        # a redirect could lead to a private address or an authentication page.
        return "operational" if 200 <= response.status < 400 else "degraded"
    finally:
        connection.close()


def load_config(path):
    config = json.loads(Path(path).read_text())
    expected = config.get("expectedNodes", 3)
    if type(expected) is not int or not 1 <= expected <= 100:
        raise ValueError("expectedNodes must be between 1 and 100")
    origins = config.get("allowedOrigins", [])
    for origin in origins:
        parsed = urllib.parse.urlsplit(origin)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("allowedOrigins must be exact origins")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise ValueError("plain HTTP origins are only allowed for local development")
    checks = config.get("checks", [])
    if not isinstance(checks, list) or len(checks) > 8:
        raise ValueError("at most eight public checks are supported")
    ids = set()
    for check in checks:
        identifier, name = check["id"], check["name"]
        if not isinstance(identifier, str) or not identifier.isascii() or not identifier.replace("-", "").isalnum() or len(identifier) > 40 or identifier in ids:
            raise ValueError("invalid or duplicate check id")
        if not isinstance(name, str) or not 1 <= len(name) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError("invalid check name")
        ids.add(identifier)
        public_target(check["url"])
    return {"expectedNodes": expected, "allowedOrigins": origins, "checks": checks}


def timestamp(value):
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Snapshot:
    def __init__(self, config, clock=time.time):
        self.config = config
        self.clock = clock
        self.lock = threading.Lock()
        self.values = {}
        self.attempted = None

    def collect(self, fetch_metric, fetch_check):
        # Single background writer. Readers only hold the lock to copy entries.
        for key, query in queries(self.config["expectedNodes"]).items():
            self._collect(key, lambda query=query: fetch_metric(query))
        for check in self.config["checks"]:
            self._collect("check:" + check["id"], lambda check=check: fetch_check(check["url"]))
        with self.lock:
            self.attempted = self.clock()

    def _collect(self, key, fetch):
        try:
            value = fetch()
        except Exception:
            # No upstream URL, IP, response body or exception reaches the API/log.
            LOG.warning("Collection failed for %s", key)
            with self.lock:
                if key in self.values:
                    value, when, _ = self.values[key]
                    self.values[key] = (value, when, False)
        else:
            with self.lock:
                self.values[key] = (value, self.clock(), True)

    def render(self):
        now = self.clock()
        with self.lock:
            values, attempted = dict(self.values), self.attempted
        deadlines = []
        states = []

        def field(key, fallback=None):
            value, when, success = values.get(key, (fallback, None, False))
            age = max(0, now - when) if when is not None else MAX_AGE_SECONDS
            if age >= MAX_AGE_SECONDS:
                value, state = fallback, "unavailable"
            elif not success or age >= REFRESH_SECONDS * 2:
                state = "stale"
            else:
                state = "fresh"
                deadlines.append(max(0, int(REFRESH_SECONDS * 2 - age)))
            states.append(state)
            return {"value": value, "state": state, "updatedAt": timestamp(when) if when is not None else None}

        fleet = {key: field(key) for key in METRICS}
        checks = []
        for check in self.config["checks"]:
            entry = field("check:" + check["id"], "unknown")
            checks.append({"id": check["id"], "name": check["name"], "status": entry.pop("value"), **entry})
        payload = {
            "schemaVersion": 1,
            "updatedAt": timestamp(attempted) if attempted is not None else None,
            "stale": any(state != "fresh" for state in states),
            "fleet": fleet,
            "checks": checks,
        }
        available = any(state != "unavailable" for state in states)
        # Never let a downstream cache extend stale data's life. Age is checked
        # again for every request; expired metric values become null.
        cache = "no-store" if payload["stale"] else f'public, max-age={min([30, *deadlines])}, must-revalidate'
        return payload, 200 if available else 503, cache


class LimitedServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, snapshot):
        super().__init__(address, handler)
        self.snapshot = snapshot
        self.slots = threading.BoundedSemaphore(16)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        request.settimeout(5)
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "HyadesOverview"
    sys_version = ""

    def log_message(self, *_args):
        pass  # Don't log request URLs, query strings, headers, or client addresses.

    def reply(self, status, body, cache="no-store", extra=None):
        raw = json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin in self.server.snapshot.config["allowedOrigins"]:
            self.send_header("Access-Control-Allow-Origin", origin)
        if status == 200:
            self.send_header("ETag", '"' + hashlib.sha256(raw).hexdigest() + '"')
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def do_GET(self):
        if self.path == PATH:
            payload, status, cache = self.server.snapshot.render()
            self.reply(status, payload, cache)
        elif self.path == "/healthz":
            self.reply(200, {"status": "running"})
        else:
            self.reply(404, {"error": "not_found"})

    do_HEAD = do_GET

    def do_OPTIONS(self):
        if self.path != PATH:
            self.reply(404, {"error": "not_found"})
        elif self.headers.get("Origin") not in self.server.snapshot.config["allowedOrigins"]:
            self.reply(403, {"error": "origin_not_allowed"})
        else:
            self.reply(200, {}, extra={"Access-Control-Allow-Methods": "GET, HEAD, OPTIONS"})

    def reject(self):
        self.reply(405, {"error": "method_not_allowed"}, extra={"Allow": "GET, HEAD, OPTIONS"})

    do_POST = do_PUT = do_PATCH = do_DELETE = do_TRACE = do_CONNECT = reject


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config(os.getenv("OVERVIEW_CONFIG", "/app/config.json"))
    base_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090").rstrip("/")
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError("PROMETHEUS_URL must be a plain internal HTTP(S) origin")
    snapshot = Snapshot(config)
    stop = threading.Event()

    def collect():
        while not stop.is_set():
            snapshot.collect(lambda query: prometheus_value(base_url, query), probe)
            stop.wait(REFRESH_SECONDS)

    threading.Thread(target=collect, name="collector", daemon=True).start()
    server = LimitedServer(("0.0.0.0", 9080), Handler, snapshot)
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
