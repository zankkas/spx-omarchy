# Install guide: Surface Pro X Omarchy

Read `docs/known-issues.md` first if anything below doesn't match your unit.

## 0. Understand the boot ritual before anything else

On the Surface Pro X, a cold plain power-on dies at the logo. To boot from
USB you must use:

> **Volume Up + Power → UEFI → Boot Configuration → select the USB**

This is not optional ceremony; it is the only reliable boot path. Configure
the UEFI supervisor password while you are in there (Security menu). It is
the security layer of this install (see known-issues: LUKS).

## 1. Assemble the recovery kit (one-time)

The installer reads a read-only `kit/` directory containing:

```
kit/
  packages/          linux-surface + firmware .pkg.tar.* files (aarch64)
  firmware/          Surface firmware files (copied to /lib/firmware/updates)
```

Provenance: these come from a prior linux-surface-on-ARM64 install or from
building the linux-surface PKGBUILDs for aarch64. (TODO in README: a
from-scratch public recipe. Until then, the skill can guide kit assembly from
an existing install.)

## 2. Build the console live USB

You need a live environment whose kernel drives the Type Cover. The reliable
recipe: clone or rebuild a linux-surface-based live USB, or take the upstream
Omarchy ISO and rebuild its default GRUB entry to add
`omarchy.n1x_recovery=1`, upstream's own recovery flag. It makes tty1 sit at
a root console instead of autostarting the (x86-only) installer TUI. The
live env needs:
`pacstrap arch-chroot genfstab repo-add sfdisk mkfs.vfat mkfs.ext4 curl`.

## 3. Network

Plug in a USB WiFi dongle (rtl8xxxu family is proven). The internal WCN3990
does not probe on SQ2. Verify reachability of both repos:

- `https://pkgs.omarchy.org/edge/aarch64` (Omarchy, unsigned DB)
- `https://arm-mirror.omarchy.org/$arch/$repo` (Arch Linux ARM, unsigned)

## 4. Run the installer

```sh
sudo bash kit/spx-omarchy-install          # dry run: read the plan
sudo bash kit/spx-omarchy-install --apply  # type ERASE /dev/nvme0n1 when asked
```

Configuration via environment (defaults shown):

```sh
SPXO_HOSTNAME=surface-x SPXO_USERNAME=<youruser> SPXO_TIMEZONE=Europe/Berlin \
SPXO_LOCALE=en_US.UTF-8 SPXO_BT_ADDR= SPXO_KIT=/run/usb/kit
```

`SPXO_BT_ADDR` is optional: set it only if your WCN399x controller comes up
without a public address (symptom: `btmgmt info` shows no address). The
installer then writes the `btaddr.service` one-shot that sets it after
bluetooth.service, and never restarts bluetoothd (that breaks the QCA
firmware download with -110/-84).

Phases: preflight, dry-run plan, typed confirm, partition (512 MiB ESP +
ext4 root), mount, local `[surface]` file repo, pacstrap, boot artifacts
to ESP, chroot config, GRUB (`arm64-efi --removable`, `09_surface_pro_x`
menuentry with the devicetree line), firmware, fail-closed verify.

## 5. First boot

Volume Up ritual again. First login at the console, then:

```sh
omarchy-provision-user
omarchy-provision-first-run
```

## 6. Post-install hardening (proven necessary)

- If SDDM rejects a correct password: the empty-username trap, see
  known-issues #4.
- Run `omarchy update` once and verify no failed units.
- If a Qt color/theme collision appears after updates, the installer already
  wired a pin hook under `~/.config/omarchy/hooks/post-update.d/`.

## 7. When it doesn't work

Give the `skills/surface-pro-x-omarchy/SKILL.md` decision trees to your AI
agent and work the symptom. The installer also drops a report
(`report-omarchy-install.txt`) next to the kit, then hand that to the agent.
