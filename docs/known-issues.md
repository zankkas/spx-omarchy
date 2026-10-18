# Known issues & diagnosis (Surface Pro X / Omarchy)

Symptom-first. Each entry: what you see → cause → fix. The agent skill
(`skills/`) turns these into guided flows.

## 1. Internal WiFi never appears
- **Cause:** the WCN3990 radio does not probe on SQ2 (firmware/DTS).
- **Fix:** USB WiFi dongle. rtl8xxxu-family (e.g. RTL8188EUS) is proven;
  check `ip link` for a `wlu*` interface. Do not spend hours on the internal
  radio — this is a closed door on SQ2.
- **If drops occur with a 2.4 GHz wireless microphone/receiver nearby:**
  2.4 GHz radios interfere (beacon loss). Pin the AP to channel 1 (worked
  when ch6/ch11 failed in testing) or move to a 5 GHz dongle — recommended.

## 2. Keyboard dead in a live USB session
- **Cause:** generic `linux-aarch64` kernel doesn't drive the Type Cover,
  and the ISO's custom DTB lacks sc8180x.
- **Fix:** use a linux-surface-kernel live environment (recovery-kit clone).
  The upstream Omarchy ISO is a boot probe only — its live session is not an
  install host for this device.

## 3. Boot dies at the logo / after GRUB "Loading Linux..."
- **Missing boot flags** (`clk_ignore_unused efi=novamap rootwait`): check
  the kernel line in `/boot/grub/grub.cfg` from the live env.
- **LUKS specifically:** three verified-correct LUKS installs produced a
  dark first boot on SQ2 — firmware-class early-console wall, no passphrase
  prompt ever shown. LUKS is experimental; supported posture is plain install
  + UEFI supervisor password. Do not retry LUKS expecting a different result.
- **Boot ritual:** always Volume Up + Power → Boot Configuration.

## 4. SDDM rejects the correct password (fresh install)
- **Cause:** the empty-username trap in SDDM's user list (accountsservice
  interplay).
- **Fix:** log in on a TTY (Ctrl+Alt+F2, console login works), verify
  `accountsservice` is installed, and check
  `/etc/sddm.conf.d/` — the installer ships autologin removal patterns;
  writing an explicit autologin conf (`20-autologin.conf`) unblocks the
  greeter; remove it once the greeter lists the user.

## 5. Bluetooth controller has no address (`btmgmt info` empty)
- **Cause:** WCN399x comes up without a public BD address.
- **Fix:** `SPXO_BT_ADDR=<addr>` at install time (writes `btaddr.service`),
  or manually via `btmgmt --index 0 public-addr <addr>`. **Never restart
  bluetoothd** — that re-initialises hci0 and the QCA firmware download
  fails (-110/-84).

## 6. GRUB menu logic errors / empty variables in entries
- GRUB 2.16 rejects `&&`/`||` inside `grub.cfg` — menuentry conditionals
  must be if/then/else.
- A GRUB drop-in is `exec tail -n +3 $0`: it prints itself, evaluates
  nothing. Any variable used inside the heredoc must be computed before it.

## 7. arch-chroot can't see /dev/mapper/* (grub-probe fails)
- arch-chroot mounts a fresh devtmpfs that hides device-mapper nodes.
- Fix: bind-mount the live env's `/dev` wholesale into the target before
  grub-mkconfig (the installer does this; relevant if you hand-roll).

## 8. Qt/Quick theme collision after Omarchy updates
- **Fix:** the installer wires a version-pin hook under
  `~/.config/omarchy/hooks/post-update.d/pin-qtquick-color-collision`. Verify
  it still runs after `omarchy update`.

## 9. pacstrap pulls huge unexpected firmware families
- `linux-firmware` is a meta that drags a 12-way split (~300 MB, NVIDIA
  included). Not a bug; disk-budget for it.

## 10. Interactive provider prompts during pacstrap
- iptables variants, jack2/pipewire-jack, qt6 multimedia: pacstrap takes the
  first default when non-interactive. Decide explicitly if you care.

## Collecting evidence for support

The installer writes `report-omarchy-install.txt` next to the kit, and the
live env tools collect logs. For post-boot issues, from a TTY:

```sh
journalctl -b -p err --no-pager | tail -50
lsusb; ip link; rfkill list
```
