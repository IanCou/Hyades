#!/usr/bin/env python3
"""Validate local safety invariants in the Tailscale HuJSON policy."""

from __future__ import annotations

import ipaddress
import json
import pathlib
import re
import sys
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "policy.hujson"
ALIAS_RE = re.compile(r"^[a-z0-9-]+$")


def strip_comments(text: str) -> str:
    """Remove HuJSON comments without treating comment markers in strings as syntax."""
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False

    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
        elif char == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
        elif char == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index : index + 2] != "*/":
                if text[index] in "\r\n":
                    output.append(text[index])
                index += 1
            if index + 1 >= len(text):
                raise ValueError("unterminated block comment")
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


def strip_trailing_commas(text: str) -> str:
    """Remove commas before closing object or array tokens, outside strings."""
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue
        output.append(char)
        index += 1
    return "".join(output)


def load_hujson(path: pathlib.Path) -> dict[str, Any]:
    cleaned = strip_trailing_commas(strip_comments(path.read_text(encoding="utf-8")))
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("top-level policy must be an object")
    return parsed


def strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def tag_reference(value: str) -> str | None:
    """Return a tag name, dropping a destination port when one is present."""
    if not value.startswith("tag:"):
        return None
    candidate, separator, port = value.rpartition(":")
    if (
        separator
        and candidate.startswith("tag:")
        and re.fullmatch(r"\d+(?:-\d+)?|\*", port)
    ):
        return candidate
    return value


def destination_host(destination: str) -> str:
    """Return a bare host or alias after removing an optional test port."""
    if destination.startswith(("autogroup:", "group:", "tag:")):
        return destination
    if destination.startswith("["):
        closing = destination.find("]")
        return destination[1:closing] if closing != -1 else destination
    try:
        ipaddress.ip_network(destination, strict=False)
        return destination
    except ValueError:
        pass
    if ":" in destination:
        return destination.rsplit(":", 1)[0]
    return destination


def is_special_or_address(value: str) -> bool:
    if value.startswith(("autogroup:", "group:", "tag:")):
        return True
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except ValueError:
        return False


def resolve_network(
    destination: str, hosts: dict[str, str]
) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    value = hosts.get(destination, destination)
    try:
        return ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None


def networks_cover(
    candidates: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
    expected: ipaddress.IPv4Network | ipaddress.IPv6Network,
) -> bool:
    intervals = sorted(
        (int(network.network_address), int(network.broadcast_address))
        for network in candidates
        if network.version == expected.version and network.overlaps(expected)
    )
    cursor = int(expected.network_address)
    end = int(expected.broadcast_address)
    for start, stop in intervals:
        if stop < cursor:
            continue
        if start > cursor:
            return False
        cursor = max(cursor, stop + 1)
        if cursor > end:
            return True
    return cursor > end


def validate(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    hosts = policy.get("hosts", {})
    tag_owners = policy.get("tagOwners", {})
    grants = policy.get("grants", [])
    tests = policy.get("tests", [])
    auto_approvers = policy.get("autoApprovers", {})
    if not isinstance(hosts, dict):
        return ["hosts must be an object"]
    if not isinstance(tag_owners, dict):
        return ["tagOwners must be an object"]
    if not isinstance(grants, list):
        return ["grants must be an array"]
    if not isinstance(tests, list):
        return ["tests must be an array"]

    for alias, value in hosts.items():
        if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
            errors.append(f"hosts key {alias!r} must use lowercase letters, digits, or hyphens")
        if not isinstance(value, str):
            errors.append(f"hosts.{alias} must be a string IP address or network")
            continue
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            errors.append(f"hosts.{alias} has invalid IP address or network {value!r}")

    referenced_tags = set()
    for section in (grants, tests, auto_approvers):
        for value in strings(section):
            tag = tag_reference(value)
            if tag is not None:
                referenced_tags.add(tag)
    for tag in sorted(referenced_tags):
        if tag not in tag_owners:
            errors.append(f"referenced tag {tag!r} is missing from tagOwners")

    destinations: list[tuple[str, str]] = []
    for grant_index, grant in enumerate(grants):
        if not isinstance(grant, dict):
            errors.append(f"grants[{grant_index}] must be an object")
            continue
        for destination in grant.get("dst", []):
            if isinstance(destination, str):
                destinations.append((f"grants[{grant_index}].dst", destination))

    for test_index, test in enumerate(tests):
        if not isinstance(test, dict):
            errors.append(f"tests[{test_index}] must be an object")
            continue
        source = test.get("src")
        if not source:
            errors.append(f"tests[{test_index}] is missing src")
        elif isinstance(source, str) and source.startswith("autogroup:"):
            errors.append(f"tests[{test_index}].src must not use autogroup: {source!r}")
        if not test.get("accept") and not test.get("deny"):
            errors.append(f"tests[{test_index}] needs at least one accept or deny destination")
        for field in ("accept", "deny"):
            for destination in test.get(field, []):
                if isinstance(destination, str):
                    destinations.append((f"tests[{test_index}].{field}", destination))

    for location, destination in destinations:
        host = destination_host(destination)
        if is_special_or_address(host):
            continue
        if host not in hosts:
            errors.append(f"{location} uses undefined host alias {host!r}")

    admin_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    admin_has_exit_node = False
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        sources = grant.get("src", [])
        destinations_for_grant = grant.get("dst", [])
        protocols = grant.get("ip", [])
        if "tag:homelab-admin" not in sources:
            continue
        if "autogroup:internet" in destinations_for_grant:
            admin_has_exit_node = True
        if "*" not in protocols:
            continue
        for destination in destinations_for_grant:
            if not isinstance(destination, str):
                continue
            network = resolve_network(destination, hosts)
            if network is not None:
                admin_networks.append(network)

    for required in (
        ipaddress.ip_network("10.0.0.0/22"),
        ipaddress.ip_network("fd00:db8::/64"),
    ):
        if not networks_cover(admin_networks, required):
            errors.append(
                f"tag:homelab-admin wildcard grants do not cover {required.with_prefixlen}"
            )
    expected_by_version = {
        4: ipaddress.ip_network("10.0.0.0/22"),
        6: ipaddress.ip_network("fd00:db8::/64"),
    }
    for network in admin_networks:
        if not network.subnet_of(expected_by_version[network.version]):
            errors.append(
                "tag:homelab-admin wildcard grant extends beyond the preserved LAN ranges: "
                f"{network.with_prefixlen}"
            )
    if not admin_has_exit_node:
        errors.append(
            "tag:homelab-admin must be a source of a grant to autogroup:internet"
        )
    return errors


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_POLICY
    if len(sys.argv) > 2:
        print(f"usage: {pathlib.Path(sys.argv[0]).name} [path]", file=sys.stderr)
        return 2
    try:
        policy = load_hujson(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot parse {path}: {exc}", file=sys.stderr)
        return 1
    errors = validate(policy)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"OK: {path} ({len(policy.get('hosts', {}))} hosts, "
        f"{len(policy.get('grants', []))} grants, {len(policy.get('tests', []))} tests)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
