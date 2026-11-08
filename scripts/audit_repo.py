#!/usr/bin/env python3
"""Check that nothing from the disc, or made from it, is in the repository.

    python3 scripts/audit_repo.py [ROOT] [--commits REV]

Looks at what git has staged, which is what the next commit holds: each file's staged content (not
the copy in the working tree, which can differ), a link by the path it points to (what git stores),
and a submodule by name only, since its files are another repository's. Outside a git checkout it
looks at every file under ROOT. With --commits, also checks every commit reachable from REV (HEAD, or
origin/main..HEAD): its author and committer must be the project's identity, it must carry a signature
(GitHub shows a commit Verified only then), and its message must hold no session link.

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
from typing import NamedTuple

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
# The emitter's two signatures (dream-recomp translator/src/emit/emit.cpp): the plain body is
# `void fn_XXXXXXXX(Ctx& c, Memory& m) {`, the resume body `static void fn_XXXXXXXX__resume(Ctx& c,
# Memory& m, std::uint32_t resume_pc) {`. A signature change there would silence this check, so a pin
# move looks at those lines.
GENERATED_CODE = re.compile(r"(static )?void fn_[0-9a-f]{8}(__resume)?\(Ctx& c, Memory& m")
# Ubuntu's snapshot server, by address or through apt's snapshot option. Packages from it come from our
# own copy on GitHub instead (docs/project-instructions.md, section 4). Split so this file doesn't match.
UBUNTU_SNAPSHOT = re.compile("snapshot" + r"\.ubuntu\.com|\bapt(-get)?\b[^\n]*\s(--snapshot|-S)\b|^Snapshot:", re.M)
# A line that starts with an address and goes on to an SH-4 instruction, as a disassembly or trace has.
DISASSEMBLY = re.compile(
    r"^\s*(0x)?[0-9a-fA-F]{8}:?\s+([0-9a-fA-F]{4}\s+)?"
    r"(mov(\.[bwl])?|sts(\.l)?|lds(\.l)?|bsr[f]?|jsr|rts|bra[f]?|bt(/s)?|bf(/s)?|nop|add|sub|cmp/\w+|"
    r"fmov(\.s)?|fadd|fmul|fmac)\s", re.M)


# The index mode (git ls-files --stage) of a submodule: its entry is a commit of another repository,
# with nothing here to read. A symbolic link's entry is a blob like a file's, holding the path it points
# to, so it needs no case of its own.
GITLINK_MODE = "160000"


class Entry(NamedTuple):
    path: pathlib.Path
    mode: str  # the index mode, or "" outside a checkout
    data: bytes | None  # the staged content, or None to read it from the path


def staged_blobs(root: pathlib.Path, oids: list[str]) -> dict[str, bytes]:
    """The objects git holds for these ids, read in one git process. An id git can't read is left
    out, and its file is then read from the working tree instead."""
    if not oids:
        return {}
    out = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                         input="".join(oid + "\n" for oid in oids).encode(),
                         capture_output=True, check=True).stdout
    blobs, at = {}, 0
    while at < len(out):
        end = out.index(b"\n", at)
        header = out[at:end].decode().split()
        at = end + 1
        if len(header) == 3:  # "<oid> <type> <size>", then the content and a newline
            size = int(header[2])
            if header[1] == "blob":
                blobs[header[0]] = out[at:at + size]
            at += size + 1
    return blobs


def tracked_files(root: pathlib.Path) -> list[Entry]:
    """What the next commit holds, from the index (git ls-files --stage, which honours the temporary
    index of `git commit -a` in a hook), or every file under root outside a checkout."""
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--stage"],
                             capture_output=True, check=True).stdout
        staged = {}  # path -> [(mode, oid)]: a conflicted path's stages all count
        for record in filter(None, out.split(b"\0")):
            meta, name = record.split(b"\t", 1)
            mode, oid, _stage = meta.decode().split()
            staged.setdefault(os.fsdecode(name), []).append((mode, oid))
        blobs = staged_blobs(root, sorted({oid for stages in staged.values()
                                           for mode, oid in stages if mode != GITLINK_MODE}))
        return [Entry(root / name, mode, None if mode == GITLINK_MODE else blobs.get(oid))
                for name, stages in staged.items() for mode, oid in dict.fromkeys(stages)]
    return [Entry(path, "", None) for path in root.rglob("*")
            if (path.is_file() or path.is_symlink())
            and not SKIP_DIRS.intersection(path.relative_to(root).parts)]


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


def audit_message(text: str, words: list[str]) -> list[str]:
    """Findings for a commit message before the commit exists (the commit-msg hook). Lines starting
    with '#' are git's comments, which it strips from the message after the hook."""
    text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    findings = []
    if SESSION_LINK.search(text):
        findings.append("a Claude session link in the message")
    if denied_words(text, words):
        findings.append("a denied word in the message")
    return findings


def audit_file(path: pathlib.Path, rel: pathlib.PurePath, words: list[str] = (),
               data: bytes | None = None) -> list[str]:
    """Findings for one file: its name and folder, and its content, which is `data` when the caller
    has it (what git staged) and otherwise read here, a link's being the path it points to."""
    findings = []
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        findings.append("a disc, binary, card or capture file type")
    if FORBIDDEN_NAMES.match(path.name):
        findings.append("a name from the disc or the build")
    if FORBIDDEN_DIRS.intersection(part.lower() for part in rel.parts[:-1]):
        findings.append("in a folder for extracted, generated or run output")
    if data is None:
        if path.is_symlink():
            data = os.fsencode(os.readlink(path))
        elif path.is_file():
            data = path.read_bytes()
        elif path.exists():
            findings.append("a folder where a file is tracked, so its content went unchecked")
            return findings
        else:
            return findings
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


USAGE = "usage: audit_repo.py [ROOT] [--commits REV] [--message FILE]"


def option(args: list[str], name: str) -> str | None:
    """Takes `name VALUE` out of args and returns VALUE, or None when name isn't there."""
    if name not in args:
        return None
    at = args.index(name)
    if at + 1 >= len(args):
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    value = args[at + 1]
    del args[at:at + 2]
    return value


def main() -> int:
    args = sys.argv[1:]
    rev = option(args, "--commits")
    # --message FILE checks that one commit message (the commit-msg hook) instead of the tracked files,
    # which the pre-commit hook has audited just before.
    message = option(args, "--message")
    root = pathlib.Path(args[0] if args else ".").resolve()
    words = denylist(root)
    if not words:
        print("note: no denylist (JGR_AUDIT_DENYLIST or .git/info/audit-denylist), so names went unchecked")
    problems = 0
    if message is not None:
        text = pathlib.Path(message).read_text(encoding="utf-8", errors="replace")
        for finding in audit_message(text, words):
            print(f"{message}: {finding}")
            problems += 1
    else:
        for entry in tracked_files(root):
            rel = entry.path.relative_to(root)
            if entry.mode == GITLINK_MODE:
                # Named, so it isn't passed over in silence: its files are another repository's,
                # which this audit doesn't reach (dream-recomp's third_party/libchdr is one).
                print(f"note: {rel.as_posix()} is a submodule, so its files weren't audited here")
                continue
            for finding in audit_file(entry.path, rel, words, entry.data):
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
