# Driving a QEMU VM console headlessly (no SPICE/noVNC client)

Recipe for installing/configuring a VM entirely from the Proxmox host CLI
(no SPICE viewer, no browser noVNC session), using `qm monitor`'s
`screendump` and `sendkey`. Built while provisioning `archvm00` and
`ubuntuvm00` (see [Arch VM runbook](./arch-vm) and
[Ubuntu VM runbook](./ubuntu-vm)); useful any time you need to script a VM
install/first-boot instead of clicking through it.

## The loop

Everything is one repeating cycle: **send input → wait → capture the
screen → look at it → decide the next input**.

```bash
# 1. Send a keystroke
ssh root@<node> "echo 'sendkey ret' | qm monitor <vmid>"

# 2. Capture the screen to a PPM, then convert to PNG (screendump only
#    writes PPM; Claude/most tools can't view that format directly)
ssh root@<node> "echo 'screendump /tmp/vm.ppm' | qm monitor <vmid>"
scp root@<node>:/tmp/vm.ppm /tmp/vm.ppm
ffmpeg -y -i /tmp/vm.ppm /tmp/vm.png
# 3. Look at /tmp/vm.png, decide what to send next
```

File size is a cheap progress signal before even looking at the image:
a black/idle screen is a few KB, a real desktop or dialog is
100–500+ KB.

## Typing actual text

`sendkey` takes a keysym name, not a character (`sendkey a`, `sendkey
shift-a` for `A`, `sendkey spc` for space, etc). [`scripts/qm-type.sh`](../../../scripts/qm-type.sh)
wraps the translation:

```bash
scripts/qm-type.sh <node-ip> <vmid> 'sudo nmcli con up "Wired connection 1"'
ssh root@<node-ip> "echo 'sendkey ret' | qm monitor <vmid>"   # newline isn't part of the typed string
```

**No working keysym for `~` or `` ` `` was found**: `qm monitor` rejects
`sendkey grave` and `sendkey shift-grave` outright ("invalid parameter").
Avoid both characters in anything you type this way; use `$HOME` instead
of `~` in paths. (This bit us mid-session: a command with `~/.ssh` silently
had the `~` dropped, turning it into `/.ssh` (an absolute root path), which
then failed with a confusing "Permission denied" that had nothing to do with
actual file permissions.)

## Gotchas, in the order we hit them

- **Mouse input is unreliable.** `mouse_move`/`mouse_button` via `qm
monitor` did not reliably reposition the cursor in our testing; clicks
  consistently landed at some fixed wrong location regardless of the
  coordinates given, surfacing as e.g. a desktop right-click context menu
  appearing instead of the intended button press. **Do everything
  keyboard-only**: Tab / Shift+Tab to move focus, arrow keys for lists,
  Enter or Space to activate (which one depends on the toolkit: GTK
  installers tended to want Space on the focused button, not Enter).
- **Confirm real focus, not just a colored border.** A colored/orange
  border around a field doesn't always mean it's focused; some toolkits
  use the same color for a _validation-error_ state on a field that was
  never actually tabbed to. The reliable tell is whether typed characters
  actually show up (or, for a text field, whether existing text becomes
  visibly _selected_ when tabbed to).
- **Shift+Tab often wraps around to the primary button.** If a page's
  last focusable control is "Next"/"Install"/whatever, backward-tabbing
  once from the first control frequently lands right on it, faster than
  counting forward through every control on the page.
- **Idle/screen-lock eats keystrokes typed right as it kicks in.** A
  command typed just as a screensaver/lock activates can get partially
  consumed by the lock screen's password field instead of your terminal;
  symptom: "Incorrect password" on a now-locked screen, and your intended
  command never shows up in the shell history. If you're going to be
  running a long sequence of commands, disable the idle lock first:

  ```bash
  # XFCE
  xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/dpms-enabled -s false
  ```

- **A single keypress can get consumed just "waking" the display** if
  DPMS/screen-blank has kicked in; low CPU usage on the qemu process is
  the tell (versus a genuine hang, which usually shows high sustained
  CPU). Send one throwaway keypress first, then the real one.
- **Automatic update-checker GUIs can steal focus mid-session** (Ubuntu's
  "Software Updater" did this to us) and swallow whatever you type next
  into their own auth dialog. If a typed command seems to vanish
  entirely, screendump and check for an unexpected popup before assuming
  input is broken.
- **A fully unresponsive console (no mouse, no keyboard, low CPU, static
  frame) sometimes just needs a clean `qm stop` + `qm start`**. A
  `qm reset` (soft reset) was not always enough to unstick it in our
  testing.
- **Detach install media _before_ triggering the guest's own reboot**,
  not after. Proxmox VMs run with `-no-shutdown`, so a guest-initiated
  reboot request has to be completed by the management layer; if the
  ISO is still attached when that happens, it can hang waiting on Proxmox
  rather than actually cycling the VM:

  ```bash
  qm set <vmid> --ide2 none,media=cdrom
  qm set <vmid> --boot order=scsi0
  ```

- **`vga: qxl` can render a persistent black screen on modern
  Ubuntu/GNOME** (X starts, cursor shows, GNOME Shell never paints). See
  the [Ubuntu VM runbook](./ubuntu-vm) for the full `qxl` → `virtio` →
  `virtio-gl` story. Short version: `vga: virtio,memory=64` for normal
  use, `vga: virtio-gl,memory=64` (needs `libgl1`/`libegl1` on the
  **host**) only while an installer with GL-dependent UI is running.
- **`virtio-gl`'s `screendump` returns `Error: no surface`.** Fine for
  actual use over noVNC/SPICE, but it means this whole screendump-driven
  workflow stops working the moment you switch to `virtio-gl`; switch
  back to plain `virtio` if you need to keep scripting console
  verification.

## Quick reference: commands that came up constantly

```bash
qm status <vmid>                                   # running/stopped
qm start <vmid> / qm stop <vmid> / qm reset <vmid>
qm config <vmid>                                    # full config dump
qm set <vmid> --<option> <value>                    # e.g. --vga, --onboot, --boot
qm agent <vmid> ping                                # qemu-guest-agent alive? (empty output = yes)
qm agent <vmid> network-get-interfaces              # guest's actual IP, if agent is running

# Host-side liveness check without a screendump: high sustained CPU on
# a static-looking screen usually means it's actually busy/crash-looping,
# not idle:
ssh root@<node> "ps aux | grep '[k]vm -id <vmid>' | awk '{print \$3, \$4}'"  # %CPU %MEM

# Confirm a static IP actually took, from the Proxmox host:
ping -c1 <ip>
```
