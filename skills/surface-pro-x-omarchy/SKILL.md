---
name: surface-pro-x-omarchy
description: >
  Guided install and troubleshooting for running Omarchy (Arch + Hyprland,
  AArch64) on a Surface Pro X (SQ1/SQ2). Use when the user wants to install
  Linux/Omarchy/Arch on a Surface Pro X, is mid-install and stuck, or reports
  a post-install fault (dead keyboard, dark boot, no WiFi, SDDM login loop,
  missing Bluetooth address, update regressions). Works with any capable AI
  agent that can read files and run commands on the machine or over SSH.
---

# Surface Pro X Omarchy: install & support skill

This skill accompanies the `spx-omarchy` installer repo. Read
`docs/known-issues.md` for the full symptom tables; this file is the
operational flow.

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
   model and size with the user before `--apply`.

## Install walkthrough (condensed)

0. **Preflight with the user:** confirm device model (SQ1 vs SQ2: SQ2 =
   Surface Pro X 2020/WiFi+LTE model 1876+ with SQ2 sticker), NVMe size,
   and that they accept an ERASE-level install.
1. **Kit check:** `kit/packages/*.pkg.tar.*` (linux-surface, headers,
   firmware, plus dosfstools and arch-install-scripts) + `kit/firmware/`
   with both `MANIFEST.sha256` files. Missing either → stop, assemble the
   kit first (see install-guide section 1: from-scratch recipe from the
   linux-surface aarch64 repo + the ALARM mirror, no prior install needed).
2. **Live USB:** must be linux-surface-based (keyboard-proven). If the user
   only has the generic Omarchy ISO: keyboard will be dead. Tell them
   before they burn an hour. Rebuild path in install-guide §2
   (`omarchy.n1x_recovery=1` console entry).
3. **Network:** USB WiFi dongle; verify both repos reachable (curl -sI).
4. **Dry run:** `sudo bash kit/spx-omarchy-install`; read the plan with the
   user: target disk, package counts, repos, verify checklist.
5. **Apply:** `--apply`, type `ERASE /dev/nvme0n1` at the prompt.
6. **Post-install:** Volume Up ritual; console login;
   `omarchy-provision-user && omarchy-provision-first-run`; then the
   hardening pass (known-issues #4, #8).

## Troubleshooting decision trees

Symptom-first. Grep the installer's `report-omarchy-install.txt` (it is
written next to the kit) before touching the console.

### "Keyboard doesn't work in the live USB"
→ Live env kernel is generic linux-aarch64 → the Type Cover is unsupported
→ rebuild/use a linux-surface live USB. Do NOT try to debug USB hid.

### "Install finished but boot goes dark after GRUB"
1. Boot the live USB, mount the target, `grep -E '^linux' /target/boot/grub/grub.cfg`
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
