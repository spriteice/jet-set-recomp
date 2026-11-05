#!/usr/bin/env python3
"""Write a .gdi that points at the disc's own .cue and .bin files, copying no track.

    python3 scripts/02_make_gdi.py "DISC_FOLDER/Jet Grind Radio (USA).cue" games/jgr/disc.gdi

dcdisc reads .gdi, .chd and .cdi, not .cue. Each track line of a .gdi is: number, start LBA, type
(4 for data, 0 for audio), sector size, file, and the byte offset of its first sector in that file.
An audio track's pregap sits at the start of its .bin in a Redump-style dump, so the offset skips it
and the LBA is where its INDEX 01 falls. The high-density area always starts at LBA 45000.
"""
from __future__ import annotations

import pathlib
import re
import sys

SECTOR_SIZE = 2352
HIGH_DENSITY_LBA = 45000
FRAMES_PER_SECOND = 75
SECONDS_PER_MINUTE = 60
DATA_TYPE = 4
AUDIO_TYPE = 0


def msf_to_frames(msf: str) -> int:
    minutes, seconds, frames = (int(part) for part in msf.split(":"))
    return (minutes * SECONDS_PER_MINUTE + seconds) * FRAMES_PER_SECOND + frames


def parse_cue(text: str) -> list[dict]:
    """The cue's tracks, in order: their file, type, pregap frames, and area."""
    tracks: list[dict] = []
    file_name = None
    high_density = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("REM HIGH-DENSITY AREA"):
            high_density = True
        elif match := re.fullmatch(r'FILE "(.+)" BINARY', line):
            file_name = match.group(1)
        elif match := re.fullmatch(r"TRACK (\d+) (\S+)", line):
            tracks.append({"number": int(match.group(1)), "mode": match.group(2),
                           "file": file_name, "index": {}, "high_density": high_density})
        elif match := re.fullmatch(r"INDEX (\d+) (\d\d:\d\d:\d\d)", line):
            tracks[-1]["index"][int(match.group(1))] = msf_to_frames(match.group(2))
    if not tracks:
        raise ValueError("no tracks in the cue")
    return tracks


def make_gdi(tracks: list[dict], size_of, folder: str = "") -> str:
    """The .gdi's text. size_of(file name) gives a track file's size in bytes."""
    lines = [str(len(tracks))]
    next_lba = 0
    for track in tracks:
        pregap = track["index"].get(1, 0)
        offset = pregap * SECTOR_SIZE
        lba = HIGH_DENSITY_LBA if track["high_density"] else next_lba + pregap
        kind = AUDIO_TYPE if track["mode"] == "AUDIO" else DATA_TYPE
        lines.append(f'{track["number"]} {lba} {kind} {SECTOR_SIZE} "{folder}{track["file"]}" {offset}')
        next_lba = lba + (size_of(track["file"]) - offset) // SECTOR_SIZE
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2
    cue = pathlib.Path(sys.argv[1]).resolve()
    out = pathlib.Path(sys.argv[2])
    if not cue.is_file():
        print(f"No .cue at {cue}. Name your disc's .cue file, with its folder.", file=sys.stderr)
        return 1
    try:
        tracks = parse_cue(cue.read_text())
        gdi = make_gdi(tracks, lambda name: (cue.parent / name).stat().st_size, cue.parent.as_posix() + "/")
    except FileNotFoundError as missing:
        print(f"The .cue names a track that isn't beside it: {missing.filename}. Keep the .cue and its "
              ".bin files together, as they were dumped.", file=sys.stderr)
        return 1
    except ValueError as bad:
        print(f"{cue.name} isn't a disc .cue this can read: {bad}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(gdi, newline="\n")
    print(f"wrote {out}: {len(tracks)} tracks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
