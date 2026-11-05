# Jet Set Recomp

A native PC port of Jet Set Radio's Dreamcast release (Jet Grind Radio in the USA), made by
recompiling the disc's SH-4 code to C++ with [dream-recomp](https://github.com/phobos665/dream-recomp)
by phobos665. It targets Windows and Linux (SteamOS included) on x86-64.

**This repository holds no game.** SEGA owns Jet Set Radio. Bring your own disc: the build reads it
and translates it on your machine, and nothing from it, or made from it, is ever committed or
published.

## Status

The translated build is playable on Windows: music, saving, loading, the tutorial and the first level
work. Two headless 600 guest-second runs reach 35,977 frames each, with 0 faults, 0 unmapped accesses
and 0 calls falling back to the interpreter; in real play, some code the translator missed still runs
interpreted. Shadows aren't drawn, a few textures are wrong, and Linux hasn't been tried on SteamOS
yet.
[docs/status.md](docs/status.md) has the current state and what's next.

## Supported disc

Jet Grind Radio (USA), MK-51058 V1.005, as a Redump-style `.cue` with three `.bin` tracks.
`data/inputs.sha256` holds its hashes. Other releases aren't supported.

## Building

Linux, with clang, CMake, Ninja, Python 3, the Vulkan headers, `glslc` and SDL3:

```sh
scripts/00_verify_inputs.sh "/path/to/Jet Grind Radio (USA)"
scripts/01_fetch_dream_recomp.sh
python3 scripts/02_make_gdi.py "/path/to/Jet Grind Radio (USA)/Jet Grind Radio (USA).cue" games/jgr/disc.gdi
python3 scripts/03_get_boot_file.py games/jgr/disc.gdi games/jgr/boot/1ST_READ.BIN
scripts/10_build_linux.sh
```

The build takes about 15 minutes. `scripts/11_build_windows.sh` cross-builds for Windows from Linux.
[docs/build-and-test-reference.md](docs/build-and-test-reference.md) has the details.

## Credits

[CREDITS.md](CREDITS.md) lists the work this is built on, above all dream-recomp by phobos665.
Jet Set Recomp is GPL-2.0 ([LICENSE](LICENSE)), as dream-recomp is.
