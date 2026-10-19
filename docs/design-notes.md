# Design notes

## Why not the upstream Omarchy path

Upstream Omarchy (n1x) ships aarch64 package lists but boots via its own
`linux-aarch64` kernel + Limine/UKI path. On SQ2 that kernel cannot drive the
Type Cover and the Limine path is unproven for the Surface boot chain. The
proven stack on this device is linux-surface + sc8180x DTB + QCOM firmware +
GRUB arm64-efi. This installer keeps that chain and takes only Omarchy's
package layer.

## Package composition

Base + `omarchy-aarch64.packages` (zram-generator, rtkit) +
`omarchy-aarch64-qualcomm.packages` (linux-firmware-qcom,
qcom-firmware-extract, systemd-ukify, vulkan-freedreno), plus core additions:
base, sudo, grub, linux-surface(+headers), networkmanager, bluez-utils,
efibootmgr. Comments/blank lines stripped, exactly as omarchy's
pkg-defaults composer does. Every package is verified resolvable
(`pacman -Sp` dry check) before pacstrap runs.

## Repositories

- `[omarchy]`: `https://pkgs.omarchy.org/edge/aarch64` (unsigned DB, so
  `SigLevel = Never`).
- `[core]/[extra]/[alarm]/[aur]`: via `https://arm-mirror.omarchy.org`
  (unsigned DB).
- `[surface]`: local file repo built from the kit's linux-surface packages
  via `repo-add offline` (the name `local` is reserved in pacman; a prior
  install failed on exactly that).

## Safety architecture

- Dry-run is the default mode; `--apply` requires typing `ERASE <target>`.
- Target must be an NVMe `TYPE=disk`; the boot media, the kit stick, and any
  USB/SD/removable device are refused. `SPXO_TARGET_DISK` overrides are
  restricted to `/dev/loop*` for testing.
- Fail-closed final verify: devicetree present in grub.cfg, root UUID,
  BOOTAA64.EFI, kernel, initramfs, DTB, firmware counts, sddm enabled,
  omarchy repo in pacman.conf, Hyprland session file present. Anything
  missing aborts with a clear message, never a "success" into a black
  screen.
- The kit stick, other USB devices, and non-target drives are never written.

## Testing philosophy

`tests/test_spx_omarchy_install.py` asserts against the installer source
text and generated fragments: every real bug that ever fired (GRUB `&&`
rejection, devtmpfs hiding `/dev/mapper`, heredoc-expansion ordering,
false-positive hook guards, fstab LUKS patterns) is codified as a regression
test. Run:

```sh
python3 tests/test_spx_omarchy_install.py installer/spx-omarchy-install
```

## History

This is the second-generation approach. The first-generation offline install
(stick-relayed package cache, hand-rolled dependency resolution) failed 13
distinct ways. The decisive lesson: never hand-roll pacman resolution; use
online pacstrap with real pacman as the only oracle.
