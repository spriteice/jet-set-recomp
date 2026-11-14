#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check that the documents still point at things that exist.

    python3 scripts/check_docs.py [ROOT] [--dream PATH] [--shared FOLDER]

Reads every Markdown file git has staged under ROOT, which is what the next commit holds (the audit
reads the same way; outside a checkout it reads every file under ROOT), and reports:

- a relative Markdown link to a file that isn't tracked. A link's #fragment isn't checked;
- a quoted section name after a document's path that names nothing in that document, as in
  `docs/project-rules.md`, "Where code goes" or [plan.md](plan.md), "Phase 1" and "Phase 2". A
  name is found when it is a heading, or the bold words that open a paragraph or a list item, which
  is how the documents name a part with no heading of its own. `docs/x.md`, section 4 needs a
  heading that starts "4.";
- a pin that disagrees: docs/status.md's "**Pin:**" line and data/baseline.json's `built_from`
  against data/dream-recomp.pin;
- a backticked word of 7 to 12 hex digits that is no commit: not here and, with --dream PATH (a
  clone of dream-recomp with its full history), not there either. Without --dream, a word that is
  no commit here is counted as not checked, since it may be dream-recomp's;
- docs/status.md over 8,000 bytes. Every thread reads it before it works, so it holds what is true
  now, and what was done goes in docs/history.md;
- with --shared FOLDER (the project's shared folder): a line of known-bugs.md with no file in
  known-bugs/, a file there with no line, and a file whose title isn't its line's.

Prints OK with what it checked and exits 0, lists each finding and exits 1, or exits 2 when it
couldn't check at all. It shows that a pointer has a target, not that the target says what the
pointer claims, so a person still reads the document.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import posixpath
import re
import subprocess
import sys
import urllib.parse
from typing import NamedTuple

STATUS = "docs/status.md"
STATUS_MAX_BYTES = 8000
PIN_FILE = "data/dream-recomp.pin"
BASELINE = "data/baseline.json"
BUG_INDEX = "known-bugs.md"
BUG_FOLDER = "known-bugs"

# Backticked hex words that are written as hashes and are no commit of either repository, each with
# the reason it is in a document. Anything else that doesn't resolve is a finding.
KNOWN_HASHES = {
    "8e7b8bd": "libchdr's commit, a submodule of dream-recomp",
    "2013fb7": "dream-recomp's 6c098df before the history was made again on 5 November (docs/history.md)",
}

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")
# An inline link or image: the text in brackets, then the target up to a space or the bracket's end.
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?[^)\n]*\)")
SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
# A document, named in backticks or by a link, and what may follow it: quoted names, or section numbers.
DOC_REF = r"(?:`(?P<code>[^`\s]+\.md)`|\[[^\]\n]*\]\((?P<link>[^)\s#]+\.md)(?:#[^)\s]*)?\))"
QUOTED = re.compile(DOC_REF + r'(?P<names>(?:(?:,|\s+and|\s+or)\s+"[^"\n]+")+)')
NUMBERED = re.compile(DOC_REF + r",\s+sections?\s+(?P<numbers>\d+(?:(?:,|\s+and|\s+to)\s+\d+)*)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
BOLD_OPENING = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?\*\*(.+?)\*\*")
HASH_WORD = re.compile(r"`([0-9a-f]{7,12})(?:\.{2,3}([0-9a-f]{7,12}))?`")
STATUS_PIN = re.compile(r"\*\*Pin:\*\*\s+`([0-9a-f]{7,40})`")
BUILT_FROM = re.compile(r"dream-recomp ([0-9a-f]{7,40})\b")
BUG_LINE = re.compile(r"^\|\s*\[(\d+)\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|")
BUG_TITLE = re.compile(r"^# Bug (\d+): (.*?)\s*$")
BUG_FILE = re.compile(r"bug-(\d+)\.md\Z")


class Finding(NamedTuple):
    path: str
    line: int  # 0 when the finding is about the whole file
    text: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.text}" if self.line else f"{self.path}: {self.text}"


def load_audit():
    """The audit, for its reading of what git has staged: both checks then see the same commit."""
    spec = importlib.util.spec_from_file_location("audit_repo", pathlib.Path(__file__).with_name("audit_repo.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def without_fences(text: str) -> str:
    """The text with every fenced code block emptied, line for line, so a command or a sample in one
    is never read as a heading, a link or a hash, and line numbers stay true."""
    out, fence = [], None
    for line in text.split("\n"):
        mark = FENCE.match(line)
        if fence is None and mark:
            fence = mark.group(1)
            out.append("")
        elif fence is not None:
            if mark and mark.group(1) == fence:
                fence = None
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def without_inline_code(text: str) -> str:
    """The text with each code span blanked to the same length, so offsets stay true."""
    return INLINE_CODE.sub(lambda found: " " * len(found.group()), text)


def named_places(text: str) -> list[str]:
    """What a quoted name can point at: each heading, and the bold words that open a paragraph or a
    list item, without the punctuation that ends them. `text` has its fences emptied already."""
    places = []
    for line in text.split("\n"):
        heading = HEADING.match(line)
        if heading:
            places.append(heading.group(1))
            continue
        bold = BOLD_OPENING.match(line)
        if bold:
            places.append(bold.group(1).rstrip(".,:;"))
    return places


def names_a_place(name: str, places: list[str]) -> bool:
    """Whether `name` is one of the places, or the start of one up to a word's end: "Phase 1" names
    "Phase 1: mapping the code" and not "Phase 10"."""
    return any(place == name or (place.startswith(name) and not place[len(name)].isalnum()) for place in places)


def check_links(rel: str, text: str, tracked: set[str], folders: set[str]) -> tuple[list[Finding], int]:
    findings, checked = [], 0
    for found in LINK.finditer(without_inline_code(text)):
        target = found.group(1)
        if SCHEME.match(target) or target.startswith("#"):
            continue  # a web page, a mail address, or a place in this same file
        path = urllib.parse.unquote(re.split(r"[#?]", target, maxsplit=1)[0])
        base = "" if path.startswith("/") else posixpath.dirname(rel)
        resolved = posixpath.normpath(posixpath.join(base, path.lstrip("/")))
        checked += 1
        line = line_of(text, found.start())
        if resolved == ".." or resolved.startswith("../"):
            findings.append(Finding(rel, line, f"the link to {target} leaves the repository"))
        elif resolved != "." and resolved not in tracked and resolved not in folders:
            findings.append(Finding(rel, line, f"the link to {target} names no tracked file ({resolved})"))
    return findings, checked


def referred_doc(rel: str, found: re.Match, docs: dict[str, str]) -> str | None:
    """The tracked document a reference names, or None when it isn't one of ours (the shared folder's
    and dream-recomp's documents are named the same way). A backticked path is read from the top of
    the repository first, as the documents write them, then from the referring file's folder."""
    folder = posixpath.dirname(rel)
    if found.group("link"):
        tries = [posixpath.join(folder, urllib.parse.unquote(found.group("link")))]
    else:
        tries = [found.group("code"), posixpath.join(folder, found.group("code"))]
    for path in tries:
        path = posixpath.normpath(path)
        if path in docs:
            return path
    return None


def section_numbers(text: str) -> list[int]:
    """`2`, `2 and 5`, `1 to 4`: the numbers named, a range filled in."""
    numbers, parts = [], re.split(r"(,|\s+and|\s+to)\s+", text)
    for at in range(0, len(parts), 2):
        number = int(parts[at])
        if at and parts[at - 1].strip() == "to":
            numbers.extend(range(numbers[-1] + 1, number))
        numbers.append(number)
    return numbers


def check_sections(rel: str, text: str, docs: dict[str, str]) -> tuple[list[Finding], int, int]:
    """Findings, how many names were checked, and how many named a document that isn't tracked here."""
    findings, checked, elsewhere = [], 0, 0
    for found in QUOTED.finditer(text):
        target = referred_doc(rel, found, docs)
        if target is None:
            elsewhere += 1
            continue
        places = named_places(docs[target])
        for name in re.findall(r'"([^"\n]+)"', found.group("names")):
            checked += 1
            if not names_a_place(name, places):
                findings.append(Finding(rel, line_of(text, found.start()),
                                        f'"{name}" is no heading of {target}, and no bold opening of a '
                                        "paragraph or list item there"))
    for found in NUMBERED.finditer(text):
        target = referred_doc(rel, found, docs)
        if target is None:
            elsewhere += 1
            continue
        headings = [match.group(1) for match in map(HEADING.match, docs[target].split("\n")) if match]
        for number in section_numbers(found.group("numbers")):
            checked += 1
            if not any(heading.startswith(f"{number}.") for heading in headings):
                findings.append(Finding(rel, line_of(text, found.start()),
                                        f'{target} has no heading that starts "{number}."'))
    return findings, checked, elsewhere


def read_pin(text: str) -> str | None:
    """The pin file's hash: its first line that isn't a comment, as scripts/01_fetch_dream_recomp.sh
    reads it. None when that isn't a full hash."""
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            pin = line.strip()
            return pin if re.fullmatch(r"[0-9a-f]{40}", pin) else None
    return None


def check_pin(files: dict[str, bytes]) -> list[Finding]:
    """The pin is written in three places, and a pin move changes all three in one commit."""
    if PIN_FILE not in files:
        return [Finding(PIN_FILE, 0, "not tracked, so the pin in the documents went unchecked")]
    pin = read_pin(files[PIN_FILE].decode("utf-8", errors="replace"))
    if pin is None:
        return [Finding(PIN_FILE, 0, "holds no full 40-digit hash")]
    findings = []
    if STATUS in files:
        status = files[STATUS].decode("utf-8", errors="replace")
        for found in STATUS_PIN.finditer(status):
            if not pin.startswith(found.group(1)):
                findings.append(Finding(STATUS, line_of(status, found.start()),
                                        f"the Pin line says {found.group(1)}, and {PIN_FILE} holds {pin[:12]}"))
    if BASELINE in files:
        try:
            built_from = json.loads(files[BASELINE]).get("built_from", "")
        except (ValueError, AttributeError) as bad:
            return findings + [Finding(BASELINE, 0, f"isn't the JSON object it should be: {bad}")]
        named = BUILT_FROM.match(str(built_from))
        if not named:
            findings.append(Finding(BASELINE, 0, 'built_from doesn\'t start "dream-recomp HASH"'))
        elif not pin.startswith(named.group(1)):
            findings.append(Finding(BASELINE, 0,
                                    f"built_from names {named.group(1)}, and {PIN_FILE} holds {pin[:12]}"))
    return findings


def hash_words(text: str) -> list[tuple[int, str]]:
    """Each backticked word that is written as a short commit hash, or the two ends of a range of
    them, with its line. `text` has its fences emptied already."""
    return [(line_of(text, found.start()), word)
            for found in HASH_WORD.finditer(text) for word in found.groups() if word]


def whole_history(path: pathlib.Path) -> bool | None:
    """Whether the git checkout at path has its full history, or None when it isn't a checkout. In a
    shallow clone, a commit that isn't found may only be missing from the clone."""
    if not (path / ".git").exists():
        return None
    shallow = subprocess.run(["git", "-C", str(path), "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True)
    return shallow.stdout.strip() == "false" if shallow.returncode == 0 else None


def commits_in(repo: pathlib.Path, words: list[str]) -> set[str]:
    """The words that name a commit in the repository, asked in one git process."""
    if not words:
        return set()
    out = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check=%(objecttype)"],
                         input="".join(f"{word}^{{commit}}\n" for word in words),
                         capture_output=True, text=True, check=True).stdout.splitlines()
    return {word for word, answer in zip(words, out) if answer == "commit"}


def check_hashes(found: dict[str, list[tuple[str, int]]], repos: list[pathlib.Path],
                 complete: bool) -> tuple[list[Finding], list[str]]:
    """Findings for words that are commits nowhere, and the words that couldn't be settled because a
    repository that might hold them wasn't given, or was given without its full history."""
    words = sorted(word for word in found if word not in KNOWN_HASHES)
    resolved = set()
    for repo in repos:
        resolved |= commits_in(repo, words)
    missing = [word for word in words if word not in resolved]
    if not complete:
        return [], missing
    return [Finding(path, line, f"`{word}` is no commit here or in dream-recomp. Correct it; or, if it "
                                "isn't one of their commits, give it its reason in KNOWN_HASHES "
                                "(scripts/check_docs.py), or write it without the backticks")
            for word in missing for path, line in found[word]], []


def check_bug_index(shared: pathlib.Path) -> tuple[list[Finding], int]:
    """known-bugs.md has one line a bug, and each bug's notes are in its own file beside it
    (docs/project-instructions.md, section 4). Every thread writes them by hand, so they drift."""
    index = shared / BUG_INDEX
    if not index.is_file():
        return [Finding(str(index), 0, "not found, so the bug list went unchecked")], 0
    findings, lines = [], {}
    for at, line in enumerate(index.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        row = BUG_LINE.match(line)
        if not row:
            continue
        number, target, title = int(row.group(1)), row.group(2), row.group(3)
        expected = f"{BUG_FOLDER}/bug-{number:03d}.md"
        if number in lines:
            findings.append(Finding(BUG_INDEX, at, f"bug {number} has a second line"))
            continue
        lines[number] = title
        if target != expected:
            findings.append(Finding(BUG_INDEX, at, f"bug {number} links {target}, not {expected}"))
            continue
        path = shared / expected
        if not path.is_file():
            findings.append(Finding(BUG_INDEX, at, f"bug {number} has no file {expected}"))
            continue
        first = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        heading = BUG_TITLE.match(first)
        if not heading or int(heading.group(1)) != number:
            findings.append(Finding(expected, 1, f'the first line isn\'t "# Bug {number}: ..."'))
        elif heading.group(2) != title:
            findings.append(Finding(expected, 1, f"the title isn't its line's in {BUG_INDEX}: "
                                                 f'"{heading.group(2)}" here, "{title}" there'))
    folder = shared / BUG_FOLDER
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        named = BUG_FILE.match(path.name)
        if not named:
            findings.append(Finding(f"{BUG_FOLDER}/{path.name}", 0, "isn't named bug-NNN.md"))
        elif int(named.group(1)) not in lines:
            findings.append(Finding(f"{BUG_FOLDER}/{path.name}", 0, f"has no line in {BUG_INDEX}"))
    if not lines:
        findings.append(Finding(BUG_INDEX, 0, "holds no bug line this check can read"))
    return findings, len(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=".", metavar="ROOT")
    parser.add_argument("--dream", metavar="PATH", help="a clone of dream-recomp with its full history")
    parser.add_argument("--shared", metavar="FOLDER", help="the project's shared folder")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        print(f"{root} is not a folder", file=sys.stderr)
        return 2

    files: dict[str, bytes] = {}
    for entry in load_audit().tracked_files(root):
        rel = entry.path.relative_to(root).as_posix()
        if entry.data is not None:
            files[rel] = entry.data
        elif entry.path.is_file() and not entry.path.is_symlink():
            files[rel] = entry.path.read_bytes()
        else:
            files[rel] = b""  # a link or a submodule: it is tracked, and has no text to read
    docs = {rel: without_fences(data.decode("utf-8", errors="replace"))
            for rel, data in files.items() if rel.lower().endswith(".md")}
    if not docs:
        print(f"{root} holds no Markdown file, so there was nothing to check", file=sys.stderr)
        return 2
    tracked = set(files)
    folders = {parent.as_posix() for rel in files for parent in pathlib.PurePosixPath(rel).parents}

    # A hash is a finding only when both repositories could be asked, each with its full history.
    # Otherwise the ones that weren't found are counted as not checked, with the reason.
    repos, unasked = [], []
    for name, path in (("ROOT", root), ("--dream", pathlib.Path(args.dream) if args.dream else None)):
        whole = whole_history(path) if path else None
        if path is None:
            unasked.append(f"{name} wasn't given")
        elif whole is None:
            if name == "--dream":
                print(f"--dream {path}: not a git checkout", file=sys.stderr)
                return 2
            unasked.append(f"{name} isn't a git checkout")
        else:
            repos.append(path)
            if not whole:
                unasked.append(f"{name} is a shallow clone")

    findings: list[Finding] = []
    links = names = elsewhere = 0
    words: dict[str, list[tuple[str, int]]] = {}
    for rel, text in sorted(docs.items()):
        found, checked = check_links(rel, text, tracked, folders)
        findings += found
        links += checked
        found, checked, outside = check_sections(rel, text, docs)
        findings += found
        names += checked
        elsewhere += outside
        for line, word in hash_words(text):
            words.setdefault(word, []).append((rel, line))
    findings += check_pin(files)
    if STATUS in files and len(files[STATUS]) > STATUS_MAX_BYTES:
        findings.append(Finding(STATUS, 0, f"{len(files[STATUS]):,} bytes, over {STATUS_MAX_BYTES:,}: every "
                                           "thread reads it before it works, so move what was done to "
                                           "docs/history.md"))
    found, unsettled = check_hashes(words, repos, complete=not unasked)
    findings += found
    bugs = None
    if args.shared:
        found, bugs = check_bug_index(pathlib.Path(args.shared))
        findings += found

    for finding in findings:
        print(finding)
    if unsettled:
        print(f"note: {len(unsettled)} hash(es) not checked ({', '.join(unasked)}): {' '.join(unsettled)}")
    if elsewhere:
        print(f"note: {elsewhere} section name(s) not checked: their documents aren't tracked here")
    checked = (f"{len(docs)} documents, {links} links, {names} section names, "
               f"{len(words) - len(unsettled)} of {len(words)} hashes")
    if bugs is not None:
        checked += f", {bugs} bug lines"
    if findings:
        print(f"NOT OK: {len(findings)} finding(s) in {checked}")
        return 1
    print(f"OK: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
