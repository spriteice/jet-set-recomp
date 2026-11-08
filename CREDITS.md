# Credits

- **[dream-recomp](https://github.com/phobos665/dream-recomp) by phobos665** (GPL-2.0): the recompiler
  and runtime Jet Set Recomp is built on. It translates the SH-4 code and runs the Dreamcast's hardware
  as native code around it. It's fetched at a pinned commit from
  [our copy](https://github.com/spriteice/dream-recomp), never vendored.
- **[Flycast](https://github.com/flyinghead/flycast)** (GPL-2.0): dream-recomp ports parts of it and
  tests against its interpreter.
- **[libchdr](https://github.com/rtissera/libchdr)** (BSD-3-Clause, and the zstd, LZMA SDK, miniz and
  dr_flac decoders it carries, under BSD, public-domain or MIT terms),
  **[toml++](https://github.com/marzer/tomlplusplus)** (MIT) and
  **[doctest](https://github.com/doctest/doctest)** (MIT, in tests only): used by dream-recomp.
- **[SDL3](https://github.com/libsdl-org/SDL)** (zlib licence): the window, input and sound.

Each is under its own licence, and every one of them lets it be part of a GPL-2.0 program. Jet Set
Recomp itself is GPL-2.0-only ([README.md](README.md), "Licence").

Jet Set Radio and Jet Grind Radio belong to SEGA. This project isn't affiliated with SEGA.
