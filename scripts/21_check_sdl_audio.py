#!/usr/bin/env python3
"""Refuse an SDL3 library that can make no sound.

    python3 scripts/21_check_sdl_audio.py LIBRARY

SDL3 opens the sound systems of Linux at run time (dlopen), so a build made without their headers
links, lists only its dummy and disk drivers, and plays silence without a word: known bug 21, a
package whose libSDL3 had no ALSA, PulseAudio or PipeWire because the sandbox lacked their headers.
The library holds the names it looks up in each system's library, so a looked-up name is the proof
that its backend was compiled in; the systems' own names prove nothing, the hint text mentions them
in every build. Prints the backends found and exits 0; exits 1 when there is none, 2 for a path that
isn't a file. scripts/20_package.sh runs it before it copies the library, and
scripts/09_setup_sandbox.sh after it has built one.
"""
import pathlib
import sys

# One looked-up name per backend. Windows: DirectSound's entry point; WASAPI is reached through COM
# and leaves no name, so an SDL3.dll passes by DirectSound, which SDL builds on Windows every time.
MARKERS = {
    "alsa": b"snd_pcm_open",
    "pulseaudio": b"pa_context_new",
    "pipewire": b"pw_init",
    "directsound": b"DirectSoundCreate8",
}


def backends(library: bytes) -> list[str]:
    """The audio backends compiled into an SDL3 library, by the names it looks up."""
    return [name for name, marker in MARKERS.items() if marker in library]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    if not path.is_file():
        print(f"{path}: not a file", file=sys.stderr)
        return 2
    found = backends(path.read_bytes())
    if not found:
        print(f"{path} has no audio backend (none of {', '.join(MARKERS)}): a game with it plays silence. "
              "On Linux, SDL3 was built without the ALSA, PulseAudio and PipeWire headers: "
              "scripts/09_setup_sandbox.sh installs them and builds SDL3 again.", file=sys.stderr)
        return 1
    print(f"{path.name}: audio backends {', '.join(found)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
