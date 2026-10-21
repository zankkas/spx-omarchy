# spx-omarchy: Omarchy on the Surface Pro X

Scripted, reproducible **Omarchy (Hyprland + Wayland) for the Surface Pro X
(SQ1/SQ2, ARM64)**.

A Surface Pro X under Windows 11 idles with 6 to 7 GB of its 8 GB already
gone. This repo turns it into a full Hyprland desktop with room to spare,
in one scripted pass.

## What you get

| Piece | What it is |
|---|---|
| `installer/spx-omarchy-install` | Fail-closed 12-phase installer (dry-run default; `--apply` requires typing `ERASE <target>`) |
| `installer/omarchy-packages/*.packages` | Omarchy AArch64 package lists (base + aarch64 + qualcomm) |
| `tests/` | 46 regression tests that run the installer's logic against real assertions |
| `skills/surface-pro-x-omarchy/` | Agent skill: guided install + per-device troubleshooting for when things don't work |
| `docs/` | Full install guide, known-issues matrix, design notes |

## Install

What you do, in order. Every step in full detail lives in
`docs/install-guide.md`.

0. **You need:** a Surface Pro X (SQ1 or SQ2; validated on SQ2) whose NVMe
   you can erase.
1. **Assemble the recovery kit** (about 10 minutes, no prior install needed):
   linux-surface kernel + headers + Surface firmware packages, downloaded
   from official upstream sources and laid out as `kit/packages/` +
   `kit/firmware/` with sha256 manifests. Exact recipe (including the two
   helper packages the installer requires): `docs/install-guide.md`,
   section 1.
2. **Build the console live USB.** It must be linux-surface-based so the
   Type Cover keyboard works; the generic Omarchy ISO live session cannot
   drive the keyboard. Build steps: `docs/install-guide.md`, section 2.
3. **Plug in a USB WiFi dongle.** The internal WCN3990 radio does not probe
   on SQ2.
4. **Run the installer** from the live USB session (as root, dongle
   connected):

   ```sh
   bash /path/to/spx-omarchy-install            # dry run: full plan, zero writes
   bash /path/to/spx-omarchy-install --apply    # then type: ERASE /dev/nvme0n1
   ```

5. **Reboot** via Volume Up + Power → Boot Configuration, select the internal
   disk. Then at first login:

   ```sh
   omarchy-provision-user && omarchy-provision-first-run
   ```

Safety posture: dry-run is the default; the target disk must be an NVMe
`TYPE=disk` that is not the boot media or any removable device; overrides are
restricted to loop devices for testing; any missing boot artifact aborts the
install instead of "succeeding" into a black screen.

## Why this exists

The Surface Pro X ships with 8 GB of RAM, and under Windows 11 that is a
machine already gasping at idle. The hardware was never the problem; Windows
was. The device now runs a full Hyprland desktop in a fraction of that
memory, and it runs a **local LLM**, something unthinkable under Windows 11
on this hardware. The point of this repo is not rescuing a machine Microsoft
dropped. It is showing how much more these devices can do than anyone
expects from them.

Getting there is genuinely hard: the internal WiFi does not probe, the Type
Cover keyboard dies in every generic ARM live environment, the stock Omarchy
installer targets x86-64 with a boot path that does not work on SQ2, and the
boot chain (kernel, devicetree, firmware, GRUB) needs Surface-specific pieces
assembled by hand. A working install traditionally takes days of blind
console debugging. An SQ2 install was driven end-to-end with this installer
and that machine is in daily service; every regression hit along the way is
codified as a test (46 and counting).

## The approach in one paragraph

Keep the proven Surface boot path (`linux-surface` kernel, the
`sc8180x-surface-pro-x` devicetree, QCOM firmware, GRUB `arm64-efi` with a
`devicetree` line and the Surface flags) and layer the Omarchy package stack
on top via online pacstrap from the Omarchy AArch64 repository plus Arch Linux
ARM mirrors. The Omarchy `linux-aarch64` kernel and Limine boot path are
deliberately not used; they do not work on SQ2.

## Honest caveats

- **Encryption (LUKS) is experimental here.** The installer implements it and
  tests cover it, but on SQ2 three fully verified LUKS installs produced a
  dark first boot (firmware-class early-console wall). The supported posture
  is a plain install plus a **Surface UEFI supervisor password**; that
  protects the boot chain, not data-at-rest. Read `docs/known-issues.md`
  before considering LUKS.
- **Kits vary.** Kernel version and firmware files differ between recovery
  kits; the skill's troubleshooting flow exists precisely because each
  Surface Pro X is a bit different.
- The USB image itself is not hosted yet; `docs/install-guide.md` documents
  building the console live USB.

## The agent skill

`skills/surface-pro-x-omarchy/SKILL.md` is written for any capable AI agent
(Claude Code, Hermes, Cursor, ...) that the user has on hand. It walks the
full install and, more importantly, carries the diagnosis decision trees for
the failure modes that differ per device: dead keyboard, dark boot, no WiFi,
SDDM login loop, missing Bluetooth address. Point your agent at the skill
file and let it drive.

## Status & provenance

- Installer validated on-device: Surface Pro X SQ2, linux-surface
  6.18.3-1-surface+ (aarch64), Omarchy edge/aarch64 repo + arm-mirror
  (Arch Linux ARM), GRUB arm64-efi.
- Repo URLs verified live: `pkgs.omarchy.org/edge/aarch64`,
  `arm-mirror.omarchy.org` (both unsigned DBs; the installer sets
  `SigLevel = Never` for exactly these two).
- Roadmap items (hosted USB image) are tracked in the project's spec folder,
  not here.

## Credits & provenance

This installer stands on other people's shoulders. It composes their work
into a path that previously didn't exist; without each of these the install
is not possible:

- **[linux-surface](https://github.com/linux-surface/linux-surface)**: the
  foundation. The `linux-surface` kernel, the `sc8180x-surface-pro-x`
  devicetree, the Surface firmware packages, and most of the install
  knowledge for this device (boot ritual, firmware handling, kernel flags)
  come from their packages and documentation. If this project helped you,
  star/sponsor them; they are the reason a Surface Pro X runs Linux at all.
- **[Omarchy](https://github.com/omacom/omarchy)** (DHH's Hyprland desktop):
  the entire userland layer: package lists (`omarchy-base.packages` etc.),
  the Omarchy runtime, its AArch64 repository, and the
  `omarchy.n1x_recovery=1` boot flag that makes its ISO usable as a console
  install host on this machine.
- **[Arch Linux ARM](https://archlinuxarm.org)**: the base AArch64 system,
  package repository, and `pacstrap` tooling (via the Omarchy arm-mirror).
- **[Hyprland](https://github.com/hyprwm/Hyprland)**: the desktop itself.

Boot-chain debugging specific to this device (the empty-DTB hang, the GRUB
`devicetree` entry, SDDM and WiFi quirks) was worked out in this project's
own install sessions and is codified in `docs/known-issues.md` and the
agent skill, but it builds on the linux-surface wiki install guide.

## License

MIT; see `LICENSE`.
