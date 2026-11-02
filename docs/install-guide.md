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

Two provenance paths exist; both are verified:

**Path A (the route this repo was built and validated on): a stage-1 install.**
Before Omarchy, put a minimal Arch ARM install with the linux-surface kernel
on the device: the Type Cover keyboard works there, so you have a
network-connected, self-hosting machine. That first install is temporary;
its pacman cache and `/lib/firmware` tree ARE the kit:

- copy the cached `linux-surface`, `linux-surface-headers`,
  `linux-firmware-msft-surface-pro-x*` packages into `kit/packages/`
- also cache `dosfstools` and `arch-install-scripts` there (the installer
  extracts `mkfs.vfat` and `pacstrap`/`arch-chroot`/`genfstab` from them if
  the live USB lacks them)
- copy `qcom/msft/surface/`, `qcom/venus-5.2/`, `ath10k/WCN3990/`, `qca/`
  from `/lib/firmware` into `kit/firmware/`

Then erase the stage-1 install and let the installer put Omarchy in its
place. Your own install is your rescue path, not a rite of passage.

**Path B (no prior install): build the kit from official upstream sources.**
Run `installer/spxo-prep` on any host with curl/tar/sha256sum (macOS, Linux,
WSL):

```sh
bash installer/spxo-prep [OUTPUT_DIR]     # default: ./kit
```

It resolves the current package versions from the upstream indexes, downloads
them, extracts the firmware payload, and writes both `MANIFEST.sha256` files,
then runs the same gate checks the installer uses. Sources:

- linux-surface packages: `https://pkg.surfacelinux.com/arch-aarch64/`
  (`linux-surface`, `linux-surface-headers`,
  `linux-firmware-msft-surface-pro-x`, `linux-firmware-msft-surface-pro-x-qcom`)
- helper packages: `dosfstools` and `arch-install-scripts` from the
  Arch Linux ARM mirror the installer already uses
  (`https://arm-mirror.omarchy.org/aarch64/{core,extra}/`)

The equivalent manual recipe, if you'd rather not run the script: download
the four Surface packages and two helper packages, extract the firmware
payloads (`tar -I zstd -xf`, then copy `usr/lib/firmware/{ath10k/WCN3990,
qcom/msft/surface,qcom/venus-5.2,qca}` into `kit/firmware/`), and generate
the manifests:

```sh
cd kit/packages && sha256sum $(ls *.pkg.tar.*) > MANIFEST.sha256
cd ../firmware && sha256sum $(find . -type f ! -name MANIFEST.sha256 | sort | sed 's|^\./||') > MANIFEST.sha256
```

The manifests are fail-closed: a kit without them is rejected.

## 2. Build the console live USB

You need a live environment whose kernel drives the Type Cover — or, for the
rebuild path below, a live environment with a root console and a USB keyboard.

The reliable recipe: take the upstream Omarchy aarch64 ISO and rebuild its
default GRUB entry to add `omarchy.n1x_recovery=1`, upstream's own recovery
flag. It makes tty1 sit at a root console instead of autostarting the
(x86-only) installer TUI. Upstream ships the menu entry in its grub.cfg but
not as the default; the rebuild flips the default (installer entry stays
selectable) and repacks the ISO with its original El Torito boot config:

```sh
bash installer/spxo-iso-rebuild --download [OUTPUT.iso]
# or from an already-downloaded upstream ISO:
bash installer/spxo-iso-rebuild /path/to/omarchy-<ver>-aarch64.iso [OUTPUT.iso]
```

The script is fail-closed: it refuses a tmpfs workdir, never writes to the
input ISO, verifies the El Torito options are readable before repacking, and
probes the rebuilt ISO to confirm the patched grub.cfg is inside. Needs
`xorriso`, `curl`, `sha256sum` and about 17 GB of disk-backed free space.

What the rebuilt ISO does on-device: the default GRUB entry lands at a root
console on tty1 (no installer TUI); the original installer entry remains
selectable in the menu. One honest caveat: the live session's kernel is the
generic Omarchy aarch64 one, so **the Type Cover keyboard is dead in the
live phase** — plug in a USB keyboard for that phase (the internal NVMe and
USB WiFi dongle work fine), or clone a linux-surface-based live USB instead
if you have one from a stage-1 install.

The live env needs:
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
- Do not add a Qt/Quick import pin. Upstream fixed the Qt 6.12 `Color`
  collision in 4.0.5 (omacom/omarchy#14553); every channel here ships zero
  unqualified palette refs, so pinning `import QtQuick` only freezes the
  shell on old QML APIs. Older guides told you to add
  `post-update.d/pin-qtquick-color-collision`; do not.

## 7. Updating an existing install

Symptom of a broken update path:

```sh
omarchy-channel-current            # unknown
pacman -Qm | grep -c omarchy       # every omarchy package listed as foreign
pacman -Syu                        # breaks dependency 'hyprland=0.56.2'
                                   # required by omarchy-hyprland-titlebars
```

`/etc/pacman.conf` lost its `[omarchy]` section, so `omarchy update` can only
move Arch Linux ARM packages. Restoring the section first is the whole fix.

```sh
bash installer/spxo-repo-restore --dry-run    # show the diff, change nothing
sudo bash installer/spxo-repo-restore         # stable channel
sudo bash installer/spxo-repo-restore --channel rc   # or edge, if you meant it
omarchy update                                # interactive; keep the prompt
```

The restore script backs up `/etc/pacman.conf`, refuses a channel whose
`omarchy.db` does not answer, proves `[omarchy]` ended up **first**, then
runs `pacman -Syy`. Order matters: pacman takes a name from the first repo
that carries it, and the Omarchy repo pins `hyprland` (0.56.2-7) in a way
that keeps `omarchy-hyprland-titlebars` satisfied, while Arch Linux ARM
hands out 0.57.0 and aborts the whole transaction.

Channels, read from the aarch64 repo databases (2026-11-02):

| channel | omarchy | hyprland | quickshell | notes |
|---|---|---|---|---|
| stable | 4.0.6-1 | 0.56.2-7 | 0.3.2.r7.g2b4501a-1 | daily-driver target |
| rc | 4.5.0rc3-1 | 0.56.2-7 | 0.3.2.r7.g2b4501a-1 | release candidate |
| edge | 4.5.0rc3-1 | 0.57.0-2 | 0.3.2.r7.g2b4501a-6 | same RC today, plus newer deps |

The installer ships with `edge`. That is the newest thing upstream publishes,
but today it is an unreleased RC (`4.5.0rc3`) and the 4.5 shell changes its
plugin API, so a locally rebuilt bar widget needs rework. Pick knowingly.

**Channel reporting is misleading on this install, by design of the upstream
tool.** `omarchy-version-channel` looks for `stable-mirror.omarchy.org` in
`/etc/pacman.d/mirrorlist`; ARM installs keep that file on Arch Linux ARM, so
it reports `unknown / stable` and `omarchy-channel-current` prints `unknown`.
Use the repo's own reader instead:

```sh
bash installer/spxo-channel
# stable (omarchy 4.0.6-1, server https://pkgs.omarchy.org/stable/aarch64,
#         first repo: omarchy)
```

**Post-update hooks: only `*.sample` is skipped.** `omarchy-hook` runs
`~/.config/omarchy/hooks/post-update.d/*` and skips files ending in
`.sample` - nothing else. Renaming a hook to `.disabled` or `.hook.off`
still runs it. Retire a hook by moving it out of the directory.

An update from 4.0.4 to 4.0.6 moved 175 packages and ran 14 migrations. Do
this on AC power, then verify:

```sh
pacman -Q omarchy omarchy-settings         # 4.0.6-1, 4.0.6-1
bash installer/spxo-channel                # channel + first repo
pacman -Qu | wc -l                         # 0
systemctl --failed                         # empty
dkms status                                # linux-surface modules still built
nmcli device status                        # wifi up
omarchy restart shell                      # then look at the bar
hyprctl configerrors                       # run inside the session, must be empty
```

Roll back from a TTY if the desktop does not come back: `pacman -U` the
cached `omarchy` and `omarchy-settings` packages, restore
`/etc/pacman.conf.bak.*`, and `git reset --hard` the `~/.config/hypr` and
`~/.config/omarchy` repos to the tag you made before updating.

## 8. When it doesn't work

Give the `skills/surface-pro-x-omarchy/SKILL.md` decision trees to your AI
agent and work the symptom. The installer also drops a report
(`report-omarchy-install.txt`) next to the kit, then hand that to the agent.
