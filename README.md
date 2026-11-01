# spx-omarchy: Omarchy on the Surface Pro X

Scripted, reproducible **Omarchy (Hyprland + Wayland) for the Surface Pro X
(SQ1/SQ2, ARM64)**.

A Surface Pro X under Windows 11 idles with 6 to 7 GB of its 8 GB already
gone. This repo turns it into a full Hyprland desktop with room to spare,
in one scripted pass.

## Why this exists

The machine is good. Windows is what makes it unusable: six to seven of its
eight gigabytes are gone before you open anything.

Behind that fight sat the setup I actually wanted. A thin, keyboard-first
Linux desktop that runs AI work fast and works remotely. Knowing it was there
is what made the fight worth finishing.

So the path is written down. A fail-closed installer, 46 regression tests, and
an agent skill that takes you from zero to a complete Omarchy setup. You hand
the skill to your agent and it does most of the work. What is left is a USB
stick, the device itself, and one or two commands.

Validated on an SQ2 in daily service.

## What you get

| Piece | What it is |
|---|---|
| `skills/surface-pro-x-omarchy/` | **The centerpiece**: agent skill that takes you from zero to installed Omarchy, and carries per-device diagnosis when anything misbehaves |
| `installer/spx-omarchy-install` | Fail-closed 12-phase installer (dry-run default; `--apply` requires typing `ERASE <target>`); the skill drives this |
| `installer/omarchy-packages/*.packages` | Omarchy AArch64 package lists (base + aarch64 + qualcomm) |
| `tests/` | 46 regression tests that run the installer's logic against real assertions |
| `docs/` | Full install guide, known-issues matrix, design notes |

## The fast path: clone it and tell your agent

To start, clone the repo in a safe location, open your agent in that folder, and say **"spx, set up the machine"**. A boot gateway (`AGENTS.md`) tells the agent to load the skill and know its lane from the first turn — you can also paste a link to [`skills/surface-pro-x-omarchy/SKILL.md`](skills/surface-pro-x-omarchy/SKILL.md) into a conversation elsewhere, but the clone is the zero-setup path. The agent does the driving; you do the confirming.

The agent builds everything it can from its side: it preflights your device (SQ1 vs SQ2, NVMe size), builds the recovery kit with `installer/spxo-prep` if you don't have one, prepares the live USB, and gives you the exact commands to run. The device-side steps are yours — rebooting into the USB (Volume Up + Power ritual), running the installer at the console, and the first login — because the agent has no access to the machine while it boots. If anything misbehaves on-device, you bring the symptom back and the agent works the decision trees with you.

Stuck at any point? Same skill: it carries the diagnosis decision trees for every known failure mode (dead keyboard, dark boot, no WiFi, SDDM login loop, missing Bluetooth address).

The skill never erases anything on its own: the installer defaults to a
dry run, and the actual install requires you to type `ERASE <target>`
yourself. Your agent reads the plan with you before anything is written.

## Install (doing it yourself)

If you'd rather drive without an agent, the full manual path is in
`docs/install-guide.md`. The short version, in order:

0. **You need:** a Surface Pro X (SQ1 or SQ2; validated on SQ2) whose NVMe
   you can erase.
1. **Assemble the recovery kit** (one-time; two routes, both proven):
   - **Stage-1 install (the route this repo was built on):** first put a
     minimal Arch ARM install with the linux-surface kernel on the device
     (the Type Cover works there). That first install is temporary; its
     pacman cache and firmware tree ARE the kit. Then erase it and install
     Omarchy on top.
   - **No prior install:** run `installer/spxo-prep` on any host (macOS,
     Linux, WSL); it builds the exact kit from official upstream sources
     in about 10 minutes.
   Layout, gates, and the stage-1 detail: `docs/install-guide.md`, section 1.
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

## The agent skill file

`skills/surface-pro-x-omarchy/SKILL.md` is self-contained: operational flow,
non-negotiables, and the symptom-first decision trees. Read it if you want
to see exactly how your agent will behave before letting it drive.

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
