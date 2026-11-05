#!/usr/bin/env python3
"""Check that nothing from the disc, or made from it, is in the repository.

    python3 scripts/audit_repo.py [ROOT]

Looks at what git tracks, plus what's staged, or at every file when ROOT isn't a git checkout.
Prints CLEAN and exits 0, or lists each finding and exits 1. This backs up
docs/project-instructions.md, section 3. It can't read intent, so a person still reads the diff.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

MAX_TEXT_BYTES = 1024 * 1024
LICENCE_NAMES = {"LICENSE"}
SKIP_DIRS = {".git", "third_party", "build", "build-host", "build-win", "__pycache__"}

# Disc images and files, built programs, card and flash images, pictures and captures.
FORBIDDEN_SUFFIXES = {
    ".cue", ".bin", ".gdi", ".chd", ".cdi", ".iso", ".raw", ".img",
    ".exe", ".dll", ".so", ".o", ".obj", ".a", ".lib",
    ".vmu", ".vms", ".vmi",
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ppm", ".tga",
    ".wav", ".adx", ".afs", ".ta", ".vram", ".regs",
}
FORBIDDEN_NAMES = re.compile(r"^(1st_read.*|jgr_boot.*|vmu-.*|2_dp\..*|sg_dpldr\..*|maigo\..*|ip\.bin)$", re.I)
FORBIDDEN_DIRS = {"gen", "boot", "extracted", "runs", "captures", "shots", ".regress"}

# Split so this file doesn't match itself.
SESSION_LINK = re.compile("claude" + r"\.ai/(code|chat|session|project)|" + "session" + r"_0[0-9A-Za-z]{12,}")
GENERATED_CODE = re.compile(r"static void fn_[0-9a-f]{8}(__resume)?\(Ctx& c, Memory& m")
# A line that starts with an address and goes on to an SH-4 instruction, as a disassembly or trace has.
DISASSEMBLY = re.compile(
    r"^\s*(0x)?[0-9a-fA-F]{8}:?\s+([0-9a-fA-F]{4}\s+)?"
    r"(mov(\.[bwl])?|sts(\.l)?|lds(\.l)?|bsr[f]?|jsr|rts|bra[f]?|bt(/s)?|bf(/s)?|nop|add|sub|cmp/\w+|"
    r"fmov(\.s)?|fadd|fmul|fmac)\s", re.M)


def tracked_files(root: pathlib.Path) -> list[pathlib.Path]:
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached"],
                             capture_output=True, check=True).stdout
        return [root / name.decode() for name in out.split(b"\0") if name]
    return [path for path in root.rglob("*")
            if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(root).parts)]


def audit_file(path: pathlib.Path, rel: pathlib.PurePath) -> list[str]:
    findings = []
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        findings.append("a disc, binary, card or capture file type")
    if FORBIDDEN_NAMES.match(path.name):
        findings.append("a name from the disc or the build")
    if FORBIDDEN_DIRS.intersection(part.lower() for part in rel.parts[:-1]):
        findings.append("in a folder for extracted, generated or run output")
    if not path.exists():
        return findings
    data = path.read_bytes()
    if b"\0" in data:
        findings.append("binary content")
        return findings
    if len(data) > MAX_TEXT_BYTES and path.name not in LICENCE_NAMES:
        findings.append(f"{len(data):,} bytes, too big for hand-written text")
    text = data.decode("utf-8", errors="replace")
    if SESSION_LINK.search(text):
        findings.append("a Claude session link")
    if GENERATED_CODE.search(text):
        findings.append("generated C++")
    if DISASSEMBLY.search(text):
        findings.append("instruction text")
    return findings


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    problems = 0
    for path in tracked_files(root):
        rel = path.relative_to(root)
        for finding in audit_file(path, rel):
            print(f"{rel.as_posix()}: {finding}")
            problems += 1
    if problems:
        print(f"NOT CLEAN: {problems} finding(s)")
        return 1
    print("CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
