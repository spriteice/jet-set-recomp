#!/usr/bin/env python3
"""Check that nothing from the disc, or made from it, is in the repository.

    python3 scripts/audit_repo.py [ROOT] [--commits REV]

Looks at what git tracks, plus what's staged, or at every file when ROOT isn't a git checkout. With
--commits, also checks every commit reachable from REV (HEAD, or origin/main..HEAD): its author and
committer must be the project's identity, it must carry a signature (GitHub shows a commit Verified only
then), and its message must hold no session link.

Words that must never appear (the maintainer's name) are kept out of the repository, because a list
here would publish them: they come from the JGR_AUDIT_DENYLIST environment variable (CI reads it from
a secret) or the file .git/info/audit-denylist, one word or phrase per line, and are checked in files
and commit messages alike. Without either, the audit says that names went unchecked.

Prints CLEAN and exits 0, or lists each finding and exits 1. This backs up
docs/project-instructions.md, section 3. It can't read intent, so a person still reads the diff.
"""
from __future__ import annotations

import os
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

IDENTITY = "Claude <noreply@anthropic.com>"

# Split so this file doesn't match itself.
SESSION_LINK = re.compile("claude" + r"\.ai/(code|chat|session|project)|" + "session" + r"_0[0-9A-Za-z]{12,}")
GENERATED_CODE = re.compile(r"static void fn_[0-9a-f]{8}(__resume)?\(Ctx& c, Memory& m")
# Ubuntu's snapshot server, by address or through apt's snapshot option. Packages from it come from our
# own copy on GitHub instead (docs/project-instructions.md, section 4). Split so this file doesn't match.
UBUNTU_SNAPSHOT = re.compile("snapshot" + r"\.ubuntu\.com|\bapt(-get)?\b[^\n]*\s(--snapshot|-S)\b|^Snapshot:", re.M)
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


def denylist(root: pathlib.Path) -> list[str]:
    text = os.environ.get("JGR_AUDIT_DENYLIST", "")
    local = root / ".git" / "info" / "audit-denylist"
    if local.is_file():
        text += "\n" + local.read_text(encoding="utf-8")
    return [word.strip() for word in re.split(r"[\n,]", text) if word.strip()]


def denied_words(text: str, words: list[str]) -> list[str]:
    return [word for word in words if re.search(r"\b" + re.escape(word) + r"\b", text, re.I)]


def is_signed(root: pathlib.Path, commit: str) -> bool:
    """Whether the commit carries a signature header (GPG or SSH; git stores both as gpgsig).

    Only its presence is checked: whose key it is, GitHub decides, and a sandbox has no key list to
    verify against. A commit without one is Unverified there whatever else is right about it.
    """
    raw = subprocess.run(["git", "-C", str(root), "cat-file", "commit", commit],
                         capture_output=True, check=True, text=True).stdout
    headers = raw.split("\n\n", 1)[0]
    return re.search(r"^gpgsig ", headers, re.M) is not None


def audit_commits(root: pathlib.Path, rev: str, words: list[str]) -> list[str]:
    """Findings for every commit reachable from rev, each as 'commit: finding'."""
    out = subprocess.run(["git", "-C", str(root), "log", "--format=%H%x1f%an <%ae>%x1f%cn <%ce>%x1f%B%x1e", rev],
                         capture_output=True, check=True, text=True).stdout
    findings = []
    for record in filter(str.strip, out.split("\x1e")):
        commit, author, committer, message = record.strip("\n").split("\x1f", 3)
        short = commit[:7]
        if author != IDENTITY:
            findings.append(f"{short}: author is not the project identity")
        if committer != IDENTITY:
            findings.append(f"{short}: committer is not the project identity")
        if not is_signed(root, commit):
            findings.append(f"{short}: not signed, so GitHub would show it Unverified")
        if SESSION_LINK.search(message):
            findings.append(f"{short}: a Claude session link in the message")
        if denied_words(" ".join((message, author, committer)), words):
            findings.append(f"{short}: a denied word in the message or identity")
    return findings


def audit_file(path: pathlib.Path, rel: pathlib.PurePath, words: list[str] = ()) -> list[str]:
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
    if path.suffix.lower() != ".md" and UBUNTU_SNAPSHOT.search(text):
        findings.append("Ubuntu's snapshot server, which is used only through our own copy")
    if denied_words(text, list(words)):
        findings.append("a denied word")
    return findings


def main() -> int:
    args = sys.argv[1:]
    rev = None
    if "--commits" in args:
        at = args.index("--commits")
        if at + 1 >= len(args):
            print("usage: audit_repo.py [ROOT] [--commits REV]", file=sys.stderr)
            return 2
        rev = args[at + 1]
        del args[at:at + 2]
    root = pathlib.Path(args[0] if args else ".").resolve()
    words = denylist(root)
    if not words:
        print("note: no denylist (JGR_AUDIT_DENYLIST or .git/info/audit-denylist), so names went unchecked")
    problems = 0
    for path in tracked_files(root):
        rel = path.relative_to(root)
        for finding in audit_file(path, rel, words):
            print(f"{rel.as_posix()}: {finding}")
            problems += 1
    if rev:
        for finding in audit_commits(root, rev, words):
            print(finding)
            problems += 1
    if problems:
        print(f"NOT CLEAN: {problems} finding(s)")
        return 1
    print("CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
