---
name: surface-pro-x-omarchy
description: >
  Guided install and troubleshooting for running Omarchy (Arch + Hyprland,
  AArch64) on a Surface Pro X (SQ1/SQ2). Use when the user wants to install
  Linux/Omarchy/Arch on a Surface Pro X, is mid-install and stuck, or reports
  a post-install fault (dead keyboard, dark boot, no WiFi, SDDM login loop,
  missing Bluetooth address, update regressions). Works with any capable AI
  agent that can read files and run commands on its host machine; the agent
  builds every artifact, the user executes the on-device steps.
---

# Surface Pro X Omarchy: install & support skill

You are the agent the user handed this skill to. Your job: take them from
zero to a working Omarchy install on their Surface Pro X, and diagnose any
fault along the way.

**Division of labor — know your lane.** You build everything that can be
built from your side: the recovery kit, the console live USB image, the
package cache, the exact command sequences. The user performs every step
that physically happens on the Surface itself: the boot ritual, running the
installer at the console, first login. Once the machine reboots into the USB,
you have NO access to it — do not pretend to run commands there. When the
user reports back a symptom, work the decision trees below with them.

Locate the repo first: this skill ships inside the `spx-omarchy` repo, and
the installer lives at the repo root (`installer/spx-omarchy-install`). If
the user copied only the skill folder, ask for the repo download before
starting. Read `docs/known-issues.md` for the full symptom tables; this file
is the operational flow.

## Non-negotiables (before any diagnosis)

1. **Boot ritual:** on a Surface Pro X, cold power-on dies at the logo. USB
   boot = Volume Up + Power → Boot Configuration → select the USB. If the
   user "can't boot", first ask whether they used the ritual.
2. **The internal WiFi (WCN3990) does not work on SQ2.** Never budget time
   for it. USB dongle only.
3. **Never restart bluetoothd** on a working system: the QCA firmware
   download then fails (-110/-84). Set addresses with `btmgmt public-addr`.
4. **Never hand-roll pacman dependency resolution.** If package resolution
   is involved, real pacman (live env or arm64 container) is the only oracle.
5. **LUKS on SQ2 currently ends in a dark first boot** even when every
   artifact verifies. Recommend plain install + UEFI supervisor password.
6. Erase-level operations: dry-run first, read the plan, confirm target
   model and size with the user before `--apply`. The user types
   `ERASE <target>` themselves — never ask them to paste a command you
   wrote that erases a disk without them having read the full plan.

## Install walkthrough (agent builds, user executes)

### Phase A — agent side (do all of this yourself)

A1. **Preflight with the user:** confirm device model (SQ1 vs SQ2: SQ2 =
    Surface Pro X 2020/WiFi+LTE, model 1876+ with SQ2 sticker), NVMe size,
    and that they accept an ERASE-level install.

A2. **Build the recovery kit** (`installer/spxo-prep`, on your host):
    produces `kit/packages/` (linux-surface kernel + headers, both Surface
    firmware packages, dosfstools, arch-install-scripts) and `kit/firmware/`
    with both `MANIFEST.sha256` files. Run it, then verify the gates it
    prints all PASS. If the user already has a kit (e.g. from a stage-1
    install), verify its manifests instead of rebuilding.

A3. **Build the console live USB** (`installer/spxo-iso-rebuild`, on your
    host): downloads the upstream Omarchy aarch64 ISO, flips the default
    GRUB entry to the n1x-recovery root console (`omarchy.n1x_recovery=1`),
    repacks with the original El Torito boot config, and verifies. The
    result boots to a root console on tty1 — no installer TUI. IMPORTANT
    caveat to state up front: the live session's kernel is the generic
    Omarchy one, so the Type Cover keyboard will be DEAD in the live phase;
    the user needs a USB keyboard (or a linux-surface-based live USB from a
    stage-1 clone) for that phase. Tell them before they flash.

A4. **Hand over a single command sheet.** The user's on-device sequence,
    in order, with nothing left to improvise:
    1. flash: `dd if=<console.iso> of=<usb-device> bs=4M status=progress
       conv=fsync` (agent gives the exact device node from the user's `lsblk`
       output; never guess a device letter)
    2. boot ritual: Volume Up + Power → Boot Configuration → select USB
    3. in the root console: connect the USB WiFi dongle, get online
       (`iwctl` if the dongle driver needs it, or `ip link` + DHCP)
    4. mount the kit: `mkdir -p /run/usb && mount /dev/<usb-part> /run/usb`
       (the kit can ride on a second partition of the same stick or a second
       stick)
    5. dry run: `bash /run/usb/kit/spx-omarchy-install` — have the user
       read the plan back to you; you check it against expectations (target
       disk model/size, package counts, repos)
    6. apply: `bash /run/usb/kit/spx-omarchy-install --apply` and the user
       types `ERASE /dev/nvme0n1` themselves
    7. reboot ritual: Volume Up + Power → Boot Configuration → internal disk
    8. first login at console: `omarchy-provision-user &&
       omarchy-provision-first-run`

A5. **Stand by.** The user walks the sheet; you do not touch the machine.
    When they report back (plan output, errors, symptoms), diagnose per the
    trees below.

### Phase B — user side (theirs, not yours)

Everything in A4's sheet. Your involvement: reading outputs back, confirming
each step before they fire it, catching wrong-device mistakes BEFORE `dd`
and before `--apply` (ask for `lsblk` output and name the exact device node
yourself, then make the user confirm it).

## Troubleshooting decision trees

Symptom-first. Ask the user for the installer's `report-omarchy-install.txt`
(it is written next to the kit) before touching anything.

### "Keyboard doesn't work in the live USB"
→ Live env kernel is generic linux-aarch64 → the Type Cover is unsupported
→ USB keyboard for the live phase, or a linux-surface-based live USB (stage-1
clone). Do NOT try to debug USB hid.

### "Install finished but boot goes dark after GRUB"
1. Have the user re-enter the live USB, mount the target, and run
   `grep -E '^linux' /target/boot/grub/grub.cfg`
2. Check: `cryptdevice`/`root=` present? `clk_ignore_unused efi=novamap
   rootwait` present? DTB (`devicetree`) line present?
3. All present + LUKS install → firmware-class wall, ADR-known; recommend
   reinstall without `--luks` + UEFI supervisor password (state the honest
   trade-off: boot-chain protection, not data-at-rest).
4. Anything missing → installer verify should have caught it; check the
   report, then the phase-12 checklist in docs/design-notes.md.

### "No WiFi at all"
→ `lsusb` for the dongle; `ip link` for `wlu*`. rtl8xxxu family expected.
No dongle → that's the fix. Dongle present, no link → firmware; `dmesg |
grep rtl`. **2.4 GHz mic/receiver interference** (beacon-loss storms in
`journalctl -k`): pin AP to channel 1 or use a 5 GHz dongle.

### "SDDM rejects my correct password"
→ TTY login (Ctrl+Alt+F2) works? → empty-username trap: install/verify
`accountsservice`, inspect `/etc/sddm.conf.d/`. Autologin conf unblocks;
remove after the greeter lists the user.

### "Bluetooth missing / no address"
→ `btmgmt info` shows no controller/address → set `SPXO_BT_ADDR` at install
or `btmgmt --index 0 public-addr <addr>`; NEVER restart bluetoothd.

### "Update broke the desktop" (Qt/Quick theme collision)
→ check `~/.config/omarchy/hooks/post-update.d/pin-qtquick-color-collision`
exists and executable; `omarchy update` again with the hook in place.

### "pacstrap / resolution weirdness" (only for kit builders)
→ real pacman in an arm64 container is the oracle; the failure log of the
hand-rolled era lives in the repo's history/docs (13 distinct failures; do
not repeat them).

## Per-device variance (why the trees, not a script)

Every Surface Pro X is a bit different: SQ1 vs SQ2 DTB, kit kernel versions,
firmware file sets, UEFI firmware revisions, USB dongle chipset. When a step
doesn't match the user's device, stop and adapt: identify the exact variant
(`cat /proc/device-tree/model`, `uname -a`, `lsusb`), then choose the
nearest known-issue and verify against it, never guess silently. Collect
evidence first (`journalctl -b -p err`, `dmesg`, report file), propose the
one-step fix, confirm before erase-level or boot-critical actions.
