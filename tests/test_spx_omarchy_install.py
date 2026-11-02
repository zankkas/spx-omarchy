#!/usr/bin/env python3
"""Regression tests for the Surface Pro X Omarchy installer.

Usage: python3 test_spx_omarchy_install.py <path-to-spx-omarchy-install>
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(sys.argv[1]).resolve()
SOURCE_TEXT = SOURCE.read_text(encoding="utf-8")


class TargetSafetyTests(unittest.TestCase):
    def test_apply_requires_exact_erase_confirmation(self):
        self.assertIn("ERASE $NVME", SOURCE_TEXT)

    def test_target_override_restricted_to_loop_devices(self):
        self.assertIn("SPXO_TARGET_DISK", SOURCE_TEXT)
        self.assertIn("/dev/loop", SOURCE_TEXT)

    def test_refuses_removable_and_usb_targets(self):
        # The script must check the disk's transport/model before apply.
        self.assertRegex(SOURCE_TEXT, r"lsblk[^\n]*-(?:o|n)[^\n]*TRAN", "must read transport type")
        self.assertRegex(SOURCE_TEXT, r"(?s)die[^\n]*(removable|USB|Recovery|SanDisk)")

    def test_target_mount_is_slash_target_and_created(self):
        self.assertIn("TARGET=/target", SOURCE_TEXT)
        self.assertIn('mkdir -p "$TARGET"', SOURCE_TEXT)


class RepositoryTests(unittest.TestCase):
    def test_local_repo_uses_non_reserved_name(self):
        self.assertRegex(SOURCE_TEXT, r"repo-add -q \w+\.db\.tar\.gz")
        self.assertNotIn("repo-add -q local.db.tar.gz", SOURCE_TEXT)
        self.assertNotIn("[local]", SOURCE_TEXT)

    def test_pacman_conf_uses_omarchy_and_alarm_mirror(self):
        self.assertIn("pkgs.omarchy.org/edge/$arch", SOURCE_TEXT)
        self.assertIn("arm-mirror.omarchy.org/$arch/$repo", SOURCE_TEXT)

    def test_network_repos_are_unsigned(self):
        # Both Omarchy's and the ALARM mirror ship unsigned databases.
        self.assertIn("SigLevel = Never", SOURCE_TEXT)


class PackageSetTests(unittest.TestCase):
    def test_installs_hyprland_stack_and_surface_kernel(self):
        for pkg in ("hyprland", "quickshell", "foot", "sddm", "uwsm",
                    "linux-surface", "linux-firmware-qcom"):
            self.assertRegex(SOURCE_TEXT, r"\b%s\b" % re.escape(pkg))

    def test_excludes_generic_kernel_and_limine_and_gnome(self):
        # Words may appear in comments; exclude lines that are only comments.
        code = "\n".join(l for l in SOURCE_TEXT.splitlines() if not l.lstrip().startswith("#"))
        for pkg in ("linux-aarch64", "limine", "gnome-shell", "gdm"):
            self.assertNotIn(pkg, code)

    def test_package_lists_are_read_from_project_files(self):
        self.assertIn("omarchy-base.packages", SOURCE_TEXT)
        self.assertIn("omarchy-aarch64.packages", SOURCE_TEXT)
        self.assertIn("omarchy-aarch64-qualcomm.packages", SOURCE_TEXT)

    def test_boot_artifact_verification_requires_linux_surface_pkgbase(self):
        self.assertIn("pkgbase", SOURCE_TEXT)
        self.assertIn("linux-surface", SOURCE_TEXT)


class BootPathTests(unittest.TestCase):
    def test_grub_is_arm64_efi_in_chroot(self):
        self.assertIn("chroot_run grub-install --target=arm64-efi", SOURCE_TEXT)
        self.assertNotIn("--target=aarch64-efi", SOURCE_TEXT)

    def test_grub_entry_carries_devicetree_and_surface_flags(self):
        self.assertIn("devicetree /dtb/linux-surface/qcom/sc8180x-surface-pro-x.dtb", SOURCE_TEXT)
        self.assertIn("clk_ignore_unused efi=novamap rootwait", SOURCE_TEXT)

    def test_generic_grub_generator_is_disabled(self):
        self.assertIn("chmod -x /etc/grub.d/10_linux", SOURCE_TEXT)

    def test_verify_stage_fails_closed_on_devicetree(self):
        # A FAIL in the verification checklist must not end in success.
        verify = SOURCE_TEXT.split("12. verification", 1)[1]
        self.assertIn("devicetree", verify)
        self.assertRegex(verify, r"FAIL.*exit 1|fail_closed", "verification must fail closed")


class ServiceTests(unittest.TestCase):
    def test_enables_sddm_not_gdm(self):
        self.assertIn("systemctl enable sddm", SOURCE_TEXT)
        self.assertNotIn("systemctl enable gdm", SOURCE_TEXT)

    def test_carries_surface_bluetooth_address_unit(self):
        self.assertIn("btaddr.service", SOURCE_TEXT)
        self.assertIn("After=bluetooth.service", SOURCE_TEXT)

    def test_masks_phantom_tpm_units(self):
        self.assertIn("systemctl mask dev-tpm0.device", SOURCE_TEXT)

    def test_installs_accountsservice_for_sddm_user_list(self):
        # SDDM needs accountsservice or it submits an empty username
        # ("Authentication for user "" failed") — installed system missed it.
        list_file = SOURCE.parent / "omarchy-packages" / "omarchy-base.packages"
        self.assertIn("accountsservice", list_file.read_text(encoding="utf-8"))

    def test_no_sddm_autologin(self):
        # Autologin removed for security during validation; the kit must
        # not reintroduce it.
        self.assertNotIn("20-autologin.conf", SOURCE_TEXT)
        self.assertNotIn("Session=hyprland", SOURCE_TEXT)

    def test_no_qtquick_import_pin(self):
        # omacom/omarchy#14548 (Qt 6.12 QtQuick/Color shadowing qs.Commons.Color)
        # was fixed upstream in #14553 and ships from 4.0.5. Pinning the import
        # freezes the shell on old QML APIs, so the installer must not do it and
        # must not ship a post-update hook that re-applies it.
        self.assertNotIn("import QtQuick 6.11", SOURCE_TEXT)
        self.assertNotIn("pin-qtquick-color-collision", SOURCE_TEXT)

    def test_omarchy_repo_is_listed_before_the_arch_repos(self):
        # pacman takes a name from the first repo that carries it. The omarchy
        # repo pins hyprland, which keeps omarchy-hyprland-titlebars satisfied;
        # ALARM's newer hyprland aborts the transaction otherwise.
        conf = SOURCE_TEXT.split("cat > /tmp/spxo-pacman.conf <<EOF", 1)[1]
        conf = conf.split("\nEOF", 1)[0]
        order = [line.strip() for line in conf.splitlines() if line.startswith("[")]
        self.assertLess(order.index("[omarchy]"), order.index("[core]"), order)
        # and ahead of every other Arch/ALARM repo, not just [core]
        for repo in ("[core]", "[extra]", "[alarm]", "[aur]"):
            self.assertLess(order.index("[omarchy]"), order.index(repo), order)

    def test_symlink_checks_use_dash_l(self):
        # -e follows absolute unit symlinks into the live environment and
        # produces false FAILs; enabled-service checks must test the link (-L).
        verify = SOURCE_TEXT.split("12. verification", 1)[1]
        self.assertNotRegex(verify, r"\[ -e '\$TARGET/etc/systemd/system/.*\.wants/")


class DryRunTests(unittest.TestCase):
    def test_offline_mode_and_tool_bootstrap_exist(self):
        self.assertIn("omarchy-pkgcache", SOURCE_TEXT)
        self.assertIn("bootstrap_runtime_tools", SOURCE_TEXT)
        self.assertIn("arch-install-scripts", SOURCE_TEXT)
        self.assertIn("/var/lib/pacman/sync", SOURCE_TEXT)
        self.assertIn("MANIFEST.sha256", SOURCE_TEXT)

    def test_dry_run_is_default_and_writes_nothing(self):
        with tempfile.TemporaryDirectory(prefix="spxo-test-") as temp:
            root = Path(temp)
            kit, out = self._fixture_kit(root)
            env = self._stub_env(root, kit)
            result = subprocess.run(
                ["bash", str(SOURCE), "--dry-run"],
                env=env, text=True, capture_output=True, check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("DRY RUN", output)
            self.assertIn(str(kit), output)
            self.assertIn("hyprland", output)
            # Default mode with no args must also be a dry run.
            result2 = subprocess.run(
                ["bash", str(SOURCE)],
                env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result2.returncode, 0, (result2.stdout + result2.stderr))
            self.assertIn("DRY RUN", result2.stdout)

    def test_generated_chroot_script_parses(self):
        with tempfile.TemporaryDirectory(prefix="spxo-test-") as temp:
            root = Path(temp)
            kit, _ = self._fixture_kit(root)
            env = self._stub_env(root, kit)
            result = subprocess.run(
                ["bash", str(SOURCE), "--dry-run"],
                env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK   generated chroot script parses", result.stdout)

    def test_apply_without_confirmation_aborts_before_partitioning(self):
        with tempfile.TemporaryDirectory(prefix="spxo-test-") as temp:
            root = Path(temp)
            kit, _ = self._fixture_kit(root)
            env = self._stub_env(root, kit)
            # Empty stdin: confirmation cannot match.
            result = subprocess.run(
                ["bash", str(SOURCE), "--apply"],
                env=env, text=True, capture_output=True, input="",
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, output)
            self.assertNotIn("3. partitioning", output)


    # ---- fixtures ----------------------------------------------------
    def _fixture_kit(self, root: Path):
        kit = root / "kit"
        firmware = root / "firmware"
        for sub in ("packages", "pkgcache/parts", "omarchy-packages"):
            (kit / sub).mkdir(parents=True)
        firmware.mkdir(parents=True)
        for directory in (kit / "packages", firmware):
            payload = directory / "fixture.txt"
            payload.write_text("fixture\n", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            (directory / "MANIFEST.sha256").write_text(
                f"{digest}  fixture.txt\n", encoding="utf-8")
        (kit / "pkgcache" / "parts" / "pkgcache.tar.partaa").write_bytes(b"")
        # Omarchy package lists referenced by the script (same dir as the script
        # expects: kit/omarchy-packages/).
        (kit / "omarchy-packages" / "omarchy-base.packages").write_text(
            "hyprland\nquickshell\nfoot\nsddm\nuwsm\n", encoding="utf-8")
        (kit / "omarchy-packages" / "omarchy-aarch64.packages").write_text(
            "zram-generator\nrtkit\n", encoding="utf-8")
        (kit / "omarchy-packages" / "omarchy-aarch64-qualcomm.packages").write_text(
            "linux-firmware-qcom\nqcom-firmware-extract\nsystemd-ukify\n"
            "vulkan-freedreno\n", encoding="utf-8")
        script = kit / "spx-omarchy-install"
        shutil.copy2(SOURCE, script)
        return kit, script

    def _stub_env(self, root: Path, kit: Path):
        bin_dir = root / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name in ("sfdisk", "mkfs.vfat", "mkfs.ext4", "pacstrap", "repo-add",
                     "arch-chroot", "genfstab", "tar", "partprobe", "wipefs",
                     "sgdisk", "blkid", "findmnt", "lsblk"):
            tool = bin_dir / name
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)
        lsblk = bin_dir / "lsblk"
        lsblk.write_text("#!/bin/sh\nprintf 'disk\\n'\n", encoding="utf-8")
        lsblk.chmod(0o755)
        id_tool = bin_dir / "id"
        id_tool.write_text("#!/bin/sh\nprintf '0\\n'\n", encoding="utf-8")
        id_tool.chmod(0o755)
        shasum = shutil.which("shasum")
        self.assertIsNotNone(shasum, "macOS shasum is needed for the test fixture")
        sha_tool = bin_dir / "sha256sum"
        sha_tool.write_text(
            f"#!/bin/sh\nexec {shasum} -a 256 \"$@\"\n", encoding="utf-8")
        sha_tool.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join((str(bin_dir), env.get("PATH", "")))
        env["SPXO_KIT"] = str(kit)
        return env


class LuksTests(unittest.TestCase):
    def test_luks_is_available_when_enabled(self):
        # Default stays plain; --luks switches to an encrypted root.
        self.assertIn("--luks", SOURCE_TEXT)
        self.assertIn("cryptsetup", SOURCE_TEXT)

    def test_luks_partition_layout(self):
        # When enabled: ESP stays unencrypted, dedicated unencrypted /boot,
        # root inside LUKS2 (argon2id) opened as cryptroot.
        self.assertIn("--type luks2", SOURCE_TEXT)
        self.assertIn("--pbkdf argon2id luksFormat", SOURCE_TEXT)
        self.assertIn("/dev/mapper/${CRYPTROOT}", SOURCE_TEXT)

    def test_luks_boot_partition_is_unencrypted_separate(self):
        # /boot must NOT end up on the encrypted volume (GRUB cryptodisk on
        # arm64 is fragile); it must be its own mount.
        self.assertIn("LBOOT", SOURCE_TEXT)
        self.assertIn('mount "$LBOOT"', SOURCE_TEXT)

    def test_luks_boot_entries_carry_cryptdevice(self):
        # Generated GRUB entries must decrypt in initramfs.
        self.assertIn("cryptdevice=UUID=${LUKS_UUID}:cryptroot", SOURCE_TEXT)
        self.assertIn("root=/dev/mapper/${CRYPTROOT}", SOURCE_TEXT)

    def test_initramfs_hooks_include_encrypt_and_keyboard(self):
        # encrypt HOOKS + keyboard support so the Type Cover can type the
        # passphrase in early userspace.
        self.assertIn("keyboard keymap block encrypt", SOURCE_TEXT)

    def test_initramfs_hooks_are_udev_based_not_systemd(self):
        # Regression 2026-10-16 (second half of the dark first boot): Omarchy's
        # default HOOKS are systemd-based; appending the legacy `encrypt` hook
        # does NOTHING under the systemd hook (silently ignored, no passphrase
        # prompt). The classic encrypt hook requires the classic udev hook set:
        # the installer must REWRITE the HOOKS line, not append to it.
        self.assertIn(
            "HOOKS=(base udev autodetect microcode modconf kms keyboard keymap block encrypt filesystems fsck)",
            SOURCE_TEXT)
        self.assertNotRegex(SOURCE_TEXT, r"HOOKS=\\1 encrypt keymap keyboard")
        verify = SOURCE_TEXT.split("12. verification", 1)[1]
        self.assertIn("systemd hook absent", verify)

    def test_persistent_journal_created(self):
        # Regression 2026-10-16: the first-boot capture came back empty --
        # no /var/log/journal existed, so the dark boot's logs were volatile
        # and lost at reboot. The installer must create the journal dir.
        chroot = SOURCE_TEXT.split("spxo-configure.sh", 1)[1]
        self.assertIn("mkdir -p /var/log/journal", chroot)

    def test_luks_verification_fails_closed(self):
        verify = SOURCE_TEXT.split("12. verification", 1)[1]
        self.assertIn("LUKS header", verify)

    def test_luks_sfdisk_has_single_explicit_start(self):
        # Regression 2026-10-15: an explicit start=2048 on the /boot line made
        # it overlap the ESP -> sfdisk "numerical result out of range". Only
        # the first partition may declare its start.
        starts = len(re.findall(r"start=2048", SOURCE_TEXT))
        self.assertEqual(starts, 1)  # only the ESP line; /boot and cryptroot auto-follow
        luks_block = re.search(r'size=\$\(\(LBOOT_MB \* 2048\)\).*\n.*name="cryptroot"', SOURCE_TEXT)
        self.assertIsNotNone(luks_block)
        self.assertNotIn("start=2048", luks_block.group(0))

    def test_no_lowercase_nvme_typo(self):
        # Regression 2026-10-15: "$NVMe" died under set -u right after
        # partitioning (step 3). The variable is "$NVME" everywhere.
        self.assertNotRegex(SOURCE_TEXT, r'\$\{?NVMe[^E_]')  # catches $NVMe and ${NVMe}

    def test_esp_check_is_luks_aware(self):
        # Regression 2026-10-15: in LUKS mode the ESP mounts at /boot/efi;
        # the phase-5 check must verify that, not /boot.
        self.assertIn('TARGET/boot/efi" 2>/dev/null', SOURCE_TEXT)
        self.assertIn("not mounted at $TARGET/boot/efi", SOURCE_TEXT)

    def test_minegrub_theme_is_integrated(self):
        # The wiped ESP takes the theme with it; the installer must restage
        # minegrub/ from the USB root and wire the GRUB_THEME drop-in.
        self.assertIn("minegrub", SOURCE_TEXT)
        self.assertIn("GRUB_THEME=/boot/grub/themes/minegrub/theme.txt", SOURCE_TEXT)
        self.assertIn("50-minegrub.cfg", SOURCE_TEXT)

    def test_encrypt_hook_inserted_inside_parens(self):
        # Regression 2026-10-15: appending the hooks AFTER the closing paren
        # made mkinitcpio's bash parser execute "encrypt" as a command
        # ("line 55: encrypt: command not found"). Since 2026-10-16 the HOOKS
        # line is REWRITTEN wholesale (systemd-based defaults are incompatible
        # with the legacy encrypt hook), which is inside-the-parens by design.
        self.assertNotRegex(SOURCE_TEXT, r"HOOKS=\\\\1 encrypt")
        self.assertIn("HOOKS=(base udev autodetect microcode modconf kms keyboard keymap block encrypt filesystems fsck)", SOURCE_TEXT)

    def test_grub_mkconfig_is_bounded_and_nvram_generators_disabled(self):
        # Regression 2026-10-15: grub-mkconfig hung inside the chroot (the
        # efibootmgr-based 31_efi_bootnext helper on bind-mounted /sys). It
        # must run under a timeout with the NVRAM helpers disabled.
        self.assertIn("chmod -x /etc/grub.d/31_efi_bootnext", SOURCE_TEXT)
        self.assertIn("timeout 600 grub-mkconfig", SOURCE_TEXT)

    def test_grub_entry_uses_if_not_and_or_chains(self):
        # Regression 2026-10-15: the 09_surface_pro_x heredoc emitted a
        # shell-style "[ ... ] && A || B" line INTO the generated grub.cfg.
        # GRUB 2.16's script language has NO &&/|| operators — grub-mkconfig
        # aborts with "syntax error at line N" (verified: even 'echo a && echo b'
        # fails grub-script-check).
        luks_heredoc = re.search(
            r"cat > /etc/grub\.d/09_surface_pro_x <<EOF2.*?^EOF2",
            SOURCE_TEXT, re.S | re.M)
        self.assertIsNotNone(luks_heredoc)
        block = luks_heredoc.group(0)
        self.assertNotIn("&&", block, "&& is not GRUB script — use if/then/else")
        self.assertNotIn("||", block, "|| is not GRUB script — use if/then/else")

    def test_luksroot_expansion_happens_at_generation_time(self):
        # Regression 2026-10-16 — THE root cause of the LUKS dark first boot.
        # The 09 drop-in is executed by grub-mkconfig as `exec tail -n +3 $0`:
        # it only PRINTS itself, it never evaluates its own lines. The
        # if/else LUKSROOT selection therefore landed verbatim (dead) in
        # grub.cfg while $LUKSROOT in the unquoted heredoc expanded at
        # generation time to EMPTY — emitted linux lines had NO root= and NO
        # cryptdevice=, so the kernel unlocked nothing and the boot went dark.
        # Invariant: LUKSROOT is computed in the shell BEFORE the heredoc; the
        # heredoc references ${LUKSROOT} and contains no if/else at all.
        heredoc_start = SOURCE_TEXT.index("cat > /etc/grub.d/09_surface_pro_x <<EOF2")
        prelude = SOURCE_TEXT[:heredoc_start]
        self.assertIn('if [ "$LUKS" = 1 ]; then', prelude)
        self.assertIn('LUKSROOT="cryptdevice=UUID=${LUKS_UUID}:cryptroot root=/dev/mapper/${CRYPTROOT}"', prelude)
        self.assertIn('else', prelude[prelude.index('if [ "$LUKS" = 1 ]; then'):])
        heredoc = re.search(
            r"cat > /etc/grub\.d/09_surface_pro_x <<EOF2.*?^EOF2",
            SOURCE_TEXT, re.S | re.M)
        assert heredoc is not None
        heredoc = heredoc.group(0)
        self.assertIn("linux /vmlinuz-linux-surface ${LUKSROOT} rw", heredoc)
        self.assertNotIn("LUKSROOT=", heredoc.split("linux /vmlinuz")[0].split("exec tail", 1)[1],
                         "no LUKSROOT assignment inside the drop-in - it would be dead code")

    def test_luks_verification_checks_linux_cmdline_args(self):
        # The old check grepped `cryptdevice` ANYWHERE in grub.cfg - it passed
        # on the dead if/else string while the linux lines had no args at all.
        # The check must require the args ON a linux cmdline.
        verify = SOURCE_TEXT.split("12. verification", 1)[1]
        self.assertIn("linux /vmlinuz.*cryptdevice=", verify)
        self.assertIn("linux /vmlinuz.*root=/dev/mapper/", verify)

    def test_luks_mode_captures_mapper_root_uuid(self):
        # Regression 2026-10-15: ROOT_UUID stayed empty in LUKS mode, so the
        # generated grub entry's else-branch carried a bare "root=UUID=".
        self.assertRegex(SOURCE_TEXT, r'ROOT_UUID=\$\(blkid -s UUID -o value "/dev/mapper/\$CRYPTROOT"')

    def test_chroot_run_binds_live_dev_not_devtmpfs(self):
        # Regression 2026-10-15: arch-chroot mounts a fresh devtmpfs on /dev
        # that lacks /dev/mapper/<cryptroot>, so grub-probe cannot canonicalize
        # the LUKS root and grub-mkconfig aborts. chroot_run must bind the
        # live env's /dev wholesale (and must not fail silently).
        self.assertNotIn("arch-chroot \"$TARGET\" \"$@\"", SOURCE_TEXT)
        self.assertIn('mount --bind "/$d" "$TARGET/$d" || die', SOURCE_TEXT)
        self.assertNotRegex(SOURCE_TEXT, r'mount --bind "/\$d" "\$TARGET/\$d" 2>/dev/null')

    def test_fstab_check_is_luks_aware(self):
        # Regression 2026-10-15: in LUKS mode fstab lists /dev/mapper/cryptroot
        # and plain /dev/nvme0n1pX entries instead of root UUIDs; the phase-12
        # check must count all device/UUID fstab entries, not just ^UUID=.
        self.assertIn("^(UUID=|/dev/)", SOURCE_TEXT)

class UpdatePathTests(unittest.TestCase):
    """The two scripts an already-installed machine needs (install-guide 7)."""

    @staticmethod
    def _fixture(extra_repo=None):
        conf = (
            "[options]\nArchitecture = aarch64\nSigLevel = Never\n\n"
            + (extra_repo or "")
            + "[core]\nInclude = /etc/pacman.d/mirrorlist\n\n"
            "[extra]\nInclude = /etc/pacman.d/mirrorlist\n\n"
            "[alarm]\nInclude = /etc/pacman.d/mirrorlist\n"
        )
        handle = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False)
        handle.write(conf)
        handle.close()
        return Path(handle.name)

    def test_repo_restore_puts_omarchy_first_in_dry_run(self):
        restore = SOURCE.parent / "spxo-repo-restore"
        conf = self._fixture()
        try:
            out = subprocess.run(
                ["bash", str(restore), "--dry-run", "--no-network",
                 "--channel", "stable"],
                env={**os.environ, "SPXO_PACMAN_CONF": str(conf)},
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("+[omarchy]", out.stdout)
            self.assertIn("+Server = https://pkgs.omarchy.org/stable/aarch64", out.stdout)
            # the diff must place the stanza above [core]
            added = out.stdout.index("+[omarchy]")
            core = out.stdout.index(" [core]")
            self.assertLess(added, core)
            # dry run must not modify the file
            self.assertNotIn("[omarchy]", conf.read_text(encoding="utf-8"))
        finally:
            conf.unlink()

    def test_repo_restore_is_idempotent_and_rejects_bad_channel(self):
        restore = SOURCE.parent / "spxo-repo-restore"
        conf = self._fixture("[omarchy]\nServer = https://pkgs.omarchy.org/edge/aarch64\n\n")
        try:
            out = subprocess.run(
                ["bash", str(restore), "--dry-run", "--no-network",
                 "--channel", "rc"],
                env={**os.environ, "SPXO_PACMAN_CONF": str(conf)},
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertNotIn("+[omarchy]", out.stdout, "must rewrite, not duplicate")
            self.assertIn("+Server = https://pkgs.omarchy.org/rc/aarch64", out.stdout)

            bad = subprocess.run(
                ["bash", str(restore), "--dry-run", "--no-network",
                 "--channel", "nightly"],
                env={**os.environ, "SPXO_PACMAN_CONF": str(conf)},
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("unknown channel", bad.stderr)
        finally:
            conf.unlink()

    def test_channel_reader_reports_from_pacman_conf_not_mirrorlist(self):
        reader = SOURCE.parent / "spxo-channel"
        conf = self._fixture("[omarchy]\nServer = https://pkgs.omarchy.org/stable/aarch64\n\n")
        try:
            out = subprocess.run(
                ["bash", str(reader), "--pacman-conf", str(conf)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("stable (omarchy", out.stdout)
            self.assertIn("first repo: omarchy", out.stdout)
        finally:
            conf.unlink()

    def test_channel_reader_flags_a_missing_omarchy_stanza(self):
        reader = SOURCE.parent / "spxo-channel"
        conf = self._fixture()
        try:
            out = subprocess.run(
                ["bash", str(reader), "--pacman-conf", str(conf)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(out.returncode, 1)
            self.assertIn("no-channel", out.stdout)
        finally:
            conf.unlink()


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])