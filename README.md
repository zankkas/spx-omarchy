# spx-omarchy — Omarchy on the Surface Pro X

Scripted, reproducible **Omarchy (Hyprland + Wayland) for the Surface Pro X
(SQ1/SQ2, ARM64)** — the machine Microsoft stopped caring about and that no
mainstream installer supports.

This project exists because installing anything modern on a Surface Pro X is
genuinely hard: the internal WiFi does not probe, the Type Cover keyboard dies
in every generic ARM live environment, the stock Omarchy installer targets
x86-64 with a Limine boot path that does not work on SQ2, and the boot chain
(kernel, devicetree, firmware, GRUB) needs Surface-specific pieces assembled
by hand. Getting one working install traditionally takes days of blind console
debugging. This repo reduces it to one script and one boot ritual — with an
AI-agent skill that supports you when your unit misbehaves.

A real install on a Surface Pro X SQ2 was driven end-to-end with this
installer; that machine is in daily service. Every regression hit along the
way is codified as a test (46 and counting).

## What you get

| Piece | What it is |
|---|---|
| `installer/spx-omarchy-install` | Fail-closed 12-phase installer (dry-run default; `--apply` requires typing `ERASE <target>`) |
| `installer/omarchy-packages/*.packages` | Omarchy AArch64 package lists (base + aarch64 + qualcomm) |
| `tests/` | 46 regression tests that run the installer's logic against real assertions |
| `skills/surface-pro-x-omarchy/` | Agent skill: guided install + per-device troubleshooting for when things don't work |
| `docs/` | Full install guide, known-issues matrix, design notes |

## The approach in one paragraph

Keep the **proven Surface boot path** — `linux-surface` kernel, the
`sc8180x-surface-pro-x` devicetree, QCOM firmware, GRUB `arm64-efi` with a
`devicetree` line and the Surface flags — and layer the **Omarchy package
stack** on top via online pacstrap from the Omarchy AArch64 repository plus
Arch Linux ARM mirrors. The Omarchy `linux-aarch64` kernel and Limine boot
path are deliberately **not** used; they do not work on SQ2. The installer
runs from a linux-surface-based live USB (keyboard-proven), builds a local
`[surface]` file repo from your recovery kit's packages, pacetrap the full
desktop, then fail-closed verifies the boot chain before declaring success.

## What you need

- A Surface Pro X (SQ1 or SQ2; validated on SQ2) with its NVMe eraseable.
- A **recovery kit** on USB: linux-surface AArch64 packages (kernel,
  headers, firmware) + Surface firmware files, as produced by a prior
  linux-surface install or built from the linux-surface PKGBUILDs. See
  `docs/install-guide.md` for assembling this — it is the one input the
  installer cannot fetch for you.
- A live USB environment based on the linux-surface kernel (so the Type
  Cover keyboard works). The generic Omarchy ISO live session will **not**
  work — its kernel can't drive the keyboard.
- A USB WiFi dongle (the internal WCN3990 radio does not probe on SQ2).

## Quickstart

```sh
# from the live USB session (root, USB WiFi dongle connected):
bash /path/to/spx-omarchy-install            # dry run: full plan, zero writes
bash /path/to/spx-omarchy-install --apply    # then type: ERASE /dev/nvme0n1
# reboot via Volume Up + Power → Boot Configuration
# first login: omarchy-provision-user && omarchy-provision-first-run
```

Safety posture: dry-run is the default; the target disk must be an NVMe
`TYPE=disk` that is not the boot media or any removable device; overrides are
restricted to loop devices for testing; any missing boot artifact aborts the
install instead of "succeeding" into a black screen.

## Honest caveats

- **Encryption (LUKS) is experimental here.** The installer implements it and
  tests cover it, but on SQ2 three fully verified LUKS installs produced a
  dark first boot (firmware-class early-console wall). The supported posture
  is a plain install plus a **Surface UEFI supervisor password** — that
  protects the boot chain, not data-at-rest. Read `docs/known-issues.md`
  before considering LUKS.
- **Kits vary.** Kernel version and firmware files differ between recovery
  kits; the skill's troubleshooting flow exists precisely because each
  Surface Pro X is a bit different.
- The USB image itself is not hosted yet — `docs/install-guide.md` documents
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
  `arm-mirror.omarchy.org` (both unsigned DBs — the installer sets
  `SigLevel = Never` for exactly these two).
- TODO: document/build the linux-surface AArch64 package provenance end to
  end so a user can assemble a kit from public sources alone.
- TODO: hostable console-USB image build.

## License

MIT — see `LICENSE`.
