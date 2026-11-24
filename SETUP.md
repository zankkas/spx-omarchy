# SETUP — for the agent, not the human

You have been handed this file. The human owns a Surface Pro X (SQ1 or SQ2) and
wants Omarchy on it. Drive; they execute on the device.

1. **Get the repo.** Clone `https://github.com/zankkas/spx-omarchy`. The
   installer and the docs live there; the skill alone is not enough.
2. **Read `skills/surface-pro-x-omarchy/SKILL.md` and follow it.** It is the
   complete flow: preflight, recovery kit, live USB, handover, first boot.
3. **Know the lane.** You build every artifact you can from your side. The human
   performs every step that physically happens on the Surface: the Volume
   Up + Power boot ritual, the installer at the console, the first login. Once
   the machine reboots, you have no access to it — do not pretend otherwise.
4. **Never erase anything.** The installer is a dry run by default, and the
   human types `ERASE <target>` themselves.
5. **No diagnosis before evidence.** Ask for the installer report or
   `journalctl` / `dmesg` before proposing a fix.

If they are not ready to install yet, tell them what they need: the device, a
USB stick, a USB WiFi dongle, and a willingness to erase the NVMe.
