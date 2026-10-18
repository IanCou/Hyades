#!/usr/bin/env bash
#
# qm-type.sh: type a literal string into a QEMU VM's console via `qm monitor`
# sendkey, one keystroke at a time.
#
# QEMU's HMP `sendkey` takes a keysym name, not a character, so punctuation and
# uppercase letters need translating (space -> spc, "-" -> minus, "A" ->
# shift-a, etc). This wraps that translation so you can just type the string
# you actually want typed. Built for driving OS installers / first-boot config
# over a Proxmox console when there's no SSH access yet, see
# docusaurus/docs/runbooks/qemu-console-automation.md for the full recipe this
# is part of (mouse input is unreliable in this setup; this script is the
# keyboard-only workaround).
#
# Usage:
#   ./qm-type.sh <node-ip> <vmid> "<string to type>"
#   ssh root@<node-ip> "echo 'sendkey ret' | qm monitor <vmid>"   # press Enter after
#
# Requires SSH access to the Proxmox node (root@<node-ip>) with the `qm`
# command available, same as any other qm monitor usage.

set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <node-ip> <vmid> \"<string>\"" >&2
  exit 1
fi

NODE=$1
VMID=$2
STR=$3

for (( i=0; i<${#STR}; i++ )); do
  c="${STR:$i:1}"
  case "$c" in
    " ") key="spc" ;;
    ".") key="dot" ;;
    ",") key="comma" ;;
    "-") key="minus" ;;
    "_") key="shift-minus" ;;
    "/") key="slash" ;;
    '"') key="shift-apostrophe" ;;
    "'") key="apostrophe" ;;
    "&") key="shift-7" ;;
    ">") key="shift-dot" ;;
    "<") key="shift-comma" ;;
    "|") key="shift-backslash" ;;
    "\\") key="backslash" ;;
    ";") key="semicolon" ;;
    ":") key="shift-semicolon" ;;
    "=") key="equal" ;;
    "!") key="shift-1" ;;
    "\$") key="shift-4" ;;
    "*") key="shift-8" ;;
    "(") key="shift-9" ;;
    ")") key="shift-0" ;;
    "{") key="shift-bracket_left" ;;
    "}") key="shift-bracket_right" ;;
    "[") key="bracket_left" ;;
    "]") key="bracket_right" ;;
    "^") key="shift-6" ;;
    "%") key="shift-5" ;;
    "+") key="shift-equal" ;;
    "?") key="shift-slash" ;;
    "@") key="shift-2" ;;
    "#") key="shift-3" ;;
    # No valid QEMU keysym for tilde/backtick was found (sendkey rejects
    # both "grave" and "shift-grave" outright); avoid "~" and "`" in any
    # string passed to this script. Use $HOME instead of ~ for paths.
    [A-Z]) key="shift-$(echo "$c" | tr 'A-Z' 'a-z')" ;;
    *) key="$c" ;;
  esac
  ssh "root@$NODE" "echo 'sendkey $key' | qm monitor $VMID" >/dev/null 2>&1
  sleep 0.05
done
