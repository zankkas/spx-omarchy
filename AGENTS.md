# SPX Omarchy

<!-- spx:gateway — persistent boot gateway. This skill is support-side; the gateway is not consumed by any fill step. -->

*Omarchy for the Surface Pro X.*

A fresh clone gives your agent everything needed to install Omarchy (Hyprland + Wayland, AArch64) on a Surface Pro X SQ1/SQ2, and to diagnose faults afterward. Until the skill is loaded, treat device state as unknown: the agent has no access to the Surface itself.

## The ritual

When the human says **"spx, set up the machine"** (or otherwise asks to install Omarchy on, fix, or troubleshoot a Surface Pro X):

1. Read `skills/surface-pro-x-omarchy/SKILL.md` and follow it. It is the complete flow: preflight, build, handover, and symptom-first diagnosis.
2. Know the lane from the start: the agent builds every artifact it can build (recovery kit, live USB, command sheets); the human performs everything that happens on the device.

## Hard bounds that hold before the skill is read

- Erase-level operations start as a dry run, and the human types `ERASE <target>` themselves.
- No diagnosis before evidence: ask for the installer report or `journalctl`/`dmesg` first.

## If the human is asking something else

Keep the boot light. Read `README.md` for orientation and answer in a few lines; load the full skill only when the topic is the machine.
