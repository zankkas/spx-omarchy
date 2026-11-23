# spx-omarchy: Omarchy on the Surface Pro X

Scripted, reproducible **Omarchy (Hyprland + Wayland) for the Surface Pro X**
(SQ1/SQ2, ARM64). An installer that stops rather than guesses, 47 regression
tests, and an agent skill that drives the whole path.

## The short version

- **What it does:** turns a Surface Pro X into a working Hyprland desktop in one
  scripted pass, with an agent doing the driving.
- **What you need:** the device (validated on SQ2), a USB stick, a USB WiFi
  dongle, and an NVMe you can erase.
- **What you get:** a keyboard-first ARM64 Linux desktop that idles in a
  fraction of the RAM Windows 11 spends before you open anything.

Under Windows 11 this machine idles with six to seven of its eight gigabytes
already gone. That is not a hardware problem. It is the reason this repo exists.

## Fast path: hand it to your agent

Paste this link into your agent:

**https://github.com/zankkas/spx-omarchy/blob/main/SETUP.md** ([same file here](SETUP.md))

It clones the repo, reads the skill, and starts the preflight. You can also
clone the repo, open your agent in that folder, and say **"spx, set up the
machine"** — the boot gateway (`AGENTS.md`) loads the skill on the first turn.

Either way the agent builds everything it can from its side: device preflight
(SQ1 vs SQ2, NVMe size), the recovery kit, the console live USB, and the exact
commands. What is left is yours, because it happens on the device: booting from
the USB (Volume Up + Power), running the installer at the console, and the first
login. If something misbehaves, bring the symptom back and the agent works the
decision trees with you.

The installer is a dry run by default. The real install requires you to type
`ERASE <target>` yourself, and the agent reads the plan with you before anything
is written.

## Do it yourself

The full manual path, with screenshots of the gates and the stage-1 detail, is
in [`docs/install-guide.md`](docs/install-guide.md). The order:

1. **Assemble the recovery kit** (one-time). Either capture it from a temporary
   linux-surface install, or run `installer/spxo-prep` on any host — macOS,
   Linux, WSL — which builds the exact kit from upstream sources in about ten
   minutes.
2. **Build the console live USB.** It must be linux-surface-based: the Type Cover
   keyboard does not work in a generic Omarchy live session.
3. **Plug in a USB WiFi dongle.** The internal WCN3990 radio does not probe on
   SQ2.
4. **Run the installer** from the live USB, as root:

   ```sh
   bash /path/to/spx-omarchy-install            # dry run: full plan, zero writes
   bash /path/to/spx-omarchy-install --apply    # then type: ERASE /dev/nvme0n1
   ```

5. **Reboot** via Volume Up + Power → Boot Configuration → internal disk.
6. **First login:** `omarchy-provision-user && omarchy-provision-first-run`.

Safety posture: dry-run is the default; the target must be an NVMe `TYPE=disk`
that is not the boot media or removable; overrides are restricted to loop
devices for testing; a missing boot artifact aborts the install instead of
"succeeding" into a black screen.

## Why it is hard

The stock path does not work here. The internal WiFi does not probe, the Type
Cover keyboard dies in every generic ARM live environment, the stock Omarchy
installer targets x86-64, and the boot chain (kernel, devicetree, firmware,
GRUB) needs Surface-specific pieces assembled by hand. A working install
traditionally takes days of blind console debugging.

The approach: keep the proven Surface boot path — `linux-surface` kernel, the
`sc8180x-surface-pro-x` devicetree, QCOM firmware, GRUB `arm64-efi` with a
`devicetree` line — and layer the Omarchy package stack on top via online
pacstrap from the Omarchy AArch64 repository plus Arch Linux ARM mirrors. The
Omarchy `linux-aarch64` kernel and Limine boot path are deliberately not used;
they do not work on SQ2.

## Verified on

- Surface Pro X **SQ2**, linux-surface 6.18.3-1-surface+ (aarch64), Omarchy
  edge/aarch64 repository + arm-mirror (Arch Linux ARM), GRUB arm64-efi. In daily
  service.
- **47/47 regression tests pass.** They run the installer's logic against real
  assertions, so a regression shows up as a failure rather than a bad install.
- Repository URLs verified live: `pkgs.omarchy.org/edge/aarch64` and
  `arm-mirror.omarchy.org` (both unsigned DBs; the installer sets
  `SigLevel = Never` for exactly these two).

**Honest caveats.** LUKS is experimental: three fully verified LUKS installs on
SQ2 produced a dark first boot, a firmware-class early-console wall. The
supported posture is a plain install plus a **Surface UEFI supervisor password**
— that protects the boot chain, not data-at-rest. Read
[`docs/known-issues.md`](docs/known-issues.md) before considering LUKS. Kits
vary between devices, which is why the skill carries decision trees instead of
one fixed script. The USB image is not hosted yet; the install guide documents
building it.

## When it breaks

`docs/known-issues.md` carries the symptom-first tables: dead keyboard, dark
boot, no WiFi, SDDM login loop, missing Bluetooth address, pacstrap surprises.
The same trees are inside the skill, so an agent can work them with you.

## Credits

This stands on other people's shoulders. Without each of these, the install is
not possible:

- **[linux-surface](https://github.com/linux-surface/linux-surface)** — the
  foundation: the kernel, the `sc8180x-surface-pro-x` devicetree, the firmware
  packages, and most of the install knowledge for this device. If this project
  helped you, star or sponsor them; they are the reason a Surface Pro X runs
  Linux at all.
- **[Omarchy](https://github.com/omacom/omarchy)** — the userland: package
  lists, runtime, AArch64 repository, and the `omarchy.n1x_recovery=1` boot flag
  that makes its ISO usable as a console install host.
- **[Arch Linux ARM](https://archlinuxarm.org)** — the base AArch64 system and
  `pacstrap`, via the Omarchy arm-mirror.
- **[Hyprland](https://github.com/hyprwm/Hyprland)** — the desktop itself.

Boot-chain debugging specific to this device — the empty-DTB hang, the GRUB
`devicetree` entry, SDDM and WiFi quirks — was worked out in this project's own
install sessions and is codified in `docs/known-issues.md` and the agent skill.

## License

MIT; see `LICENSE`.
