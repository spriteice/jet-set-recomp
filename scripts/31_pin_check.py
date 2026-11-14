#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check the build at the pin in data/dream-recomp.pin, in one command.

    python3 scripts/31_pin_check.py CAPTURES --disc FOLDER [--before FOLDER] [--jobs N] [--label NAME]

It measures what a pin move needs measured (docs/project-instructions.md, section 2), on Linux, with
the commands of docs/build-and-test-reference.md, "The regression gate" and "The 10-minute runs":

1. it checks the disc in FOLDER (or JGR_DISC_DIR) and the boot file with scripts/00_verify_inputs.sh,
   as every boot of the game starts, and checks that the disc image the game's config names is the
   one scripts/02_make_gdi.py writes for that folder: the disc that was checked is then the disc the
   program reads;
2. it builds with scripts/10_build_linux.sh, the build's output going to build-linux.log. It builds
   every time, so that a build left from another pin is never measured under this one's name;
3. it captures the regression gate with dream-recomp's tools/regress/gate.py, each recording of the
   baseline as a replay scenario. With --before FOLDER, the gate's files of a capture made before
   the change (a capture folder's gate/), it compares the two;
4. it makes every run of data/baseline.json: --rtc-seed 1 --max-seconds N --report FILE
   --write-hash FILE, with the run's own presses and a memory card that doesn't exist yet, as the
   run's entry says. A run that plays a recording back is the gate's replay scenario, argument for
   argument, so it is made once, by the gate, and its report is the gate's;
5. it compares the runs with scripts/30_compare_runs.py --all;
6. it writes the capture folder CAPTURES/<commit>-<pin>, or <commit>-<pin>-NAME with --label NAME:
   MANIFEST.txt (the commit, the full pin, the SHA-256 of every file in scripts/, the
   `clang --version` line, the date and the commands), gate/ and runs/ (hashes, counters and
   reports), and evidence/gate.txt and evidence/ten-minute-runs.txt for the review pack.

CAPTURES is the shared folder's captures/, never a folder of this checkout. <commit> is HEAD and
<pin> the pin file as the working tree has it, 7 digits each: a pin move is checked before its commit
exists, so the manifest lists each file that differs from HEAD, as it was before the build, with its
SHA-256. A file of the checkout that changes while the check runs is a finding. A capture folder is
never written over.

The gate's capture and the runs go --jobs at a time: half as many as the machine has CPUs, unless
you say. Sharing the machine slows a run, so a run made that way whose speed is more than 15% under
the baseline's is made again alone, after everything else has ended, and both reports are kept. The
evidence says how each speed was measured.

Nothing that runs the game or reaches the network runs without a time limit: the build is stopped
after 90 minutes, and a run or the gate's capture after 6 host seconds for each guest second.

Prints what it is doing, then one of three results. UNCHANGED, exit 0: every run matches the
baseline and the gate is identical to --before. RUNS MATCH, GATE NOT COMPARED, exit 0: the same
with no --before given. NOT UNCHANGED, exit 1, with each finding: something differs, or something
could not be measured. The capture folder is written each time: it is the record. Exits 2 when it
can't check, with a line that says why: at its inputs, before anything is built or run, or later,
when a folder can't be written or an error of its own stops it. Nothing printed before an exit 2 is
a result, and measurements that were whole by then stay in the sandbox, where it says.

What the program, the build and the gate print stays in the sandbox, in build/pin-check-logs/ and
build-linux.log, because it can hold the game's own text or generated code: the evidence quotes only
the gate's own result lines. The memory cards stay there too.

It measures, and judges nothing. A changed hash or count is explained by hand, and
data/baseline.json and the pin move are the maintainer's to approve.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import fcntl
import hashlib
import importlib.util
import os
import pathlib
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import tomllib
import traceback
import typing

sys.dont_write_bytecode = True  # loading the scripts below leaves nothing behind in scripts/

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIN_FILE = "data/dream-recomp.pin"
BASELINE = "data/baseline.json"
INPUTS = "data/inputs.sha256"
CONFIG = "games/jgr/jgr.toml"
GAME = "jgr"
BUILD = "build"
PROGRAM = f"{BUILD}/games/{GAME}/{GAME}_boot"
VERIFY = "scripts/00_verify_inputs.sh"
MAKE_GDI = "scripts/02_make_gdi.py"
BUILD_SCRIPT = "scripts/10_build_linux.sh"
BUILD_LOG = "build-linux.log"
COMPARE = "scripts/30_compare_runs.py"
DREAM = "third_party/dream-recomp"
GATE = f"{DREAM}/tools/regress/gate.py"
GATE_STORE = f"{DREAM}/.regress"  # where gate.py keeps its captures, by label
GATE_LABEL = "pin-check-"  # starts this script's labels there, so it only ever removes its own
LOCK = f"{BUILD}/pin-check.lock"
LOGS = f"{BUILD}/pin-check-logs"
MARKER = "IN-PROGRESS.txt"
BUILDING = 'docs/build-and-test-reference.md, "Building", steps 1 to 3'

# What a gate capture holds that may leave the sandbox: hashes, counts and the list of scenarios. The
# gate leaves its replay's memory card beside them, and a card never leaves
# (docs/project-instructions.md, section 3).
GATE_FILES = ("*.hash", "*.counters", "*.report", "scenarios")
# A baseline run that plays a recording back is NAME_replay, and the gate's scenario for it is NAME,
# as docs/build-and-test-reference.md, "The regression gate" names it.
REPLAY_SUFFIX = "_replay"
# The keys of a baseline run that say how the run is made, each of which becomes arguments below, and
# the keys that only describe it. Together they are the compare script's DESCRIPTIONS: a description
# added there that this script doesn't know stops it, so no run is made without one of its arguments.
HOW_A_RUN_IS_MADE = {"press", "vmu", "replay_input", "max_seconds"}
ABOUT_A_RUN = {"reproduced_on", "recorded_on"}
# A run that hasn't ended after this many host seconds for each guest second is stopped: a sixth of
# real time, about a tenth of the baseline's slowest speed.
HOST_SECONDS_A_GUEST_SECOND = 6
# The gate's own two scenarios, attract and gameplay, are 40 s of guest time each
# (docs/build-and-test-reference.md, "The regression gate"). Its capture gets the runs' limit for
# those and its replays together. The gate also stops each scenario itself, after an hour.
GATE_OWN_GUEST_SECONDS = 80
BUILD_LIMIT_SECONDS = 90 * 60  # six times the 15 minutes the build reference gives a build
GRACE_SECONDS = 10  # between asking a process to end and ending it
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")  # names a file or a folder, and nothing else
PLAIN_ARGUMENT = re.compile(r"[\w@%+=:,./$-]+\Z")
# The gate's own result lines, as tools/regress/gate.py prints them. Only these are quoted in the
# evidence. When a scenario writes no hash, the gate prints the last line the program printed, which
# can be the game's own text, so every other line stays in the sandbox and is only counted.
SCENARIO = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
DIGEST = r"[0-9a-f]{16}"
GATE_COMPARE_LINES = re.compile(
    rf"  {SCENARIO}\s+(identical|CHANGED  writehash {DIGEST} -> {DIGEST}(   counters differ too)?"
    rf"|MISSING [\w./-]+ -- capture it before comparing)\Z"
    r"|  A changed hash is a fact; whether it matters is a judgement\. Understand it before continuing\.\Z")


def gate_capture_lines(label: str) -> re.Pattern:
    """The line the gate's capture prints for each scenario it captured under `label`."""
    return re.compile(rf"  {re.escape(label)}\s+{SCENARIO}\s+frames=\d+\s+writehash={DIGEST} counters={DIGEST}\Z")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.lstrip("0123456789_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare_runs = load("30_compare_runs")
make_gdi = load("02_make_gdi")


class CannotCheck(Exception):
    """An input that leaves nothing to check: the message says which, and what to do."""


class Ending(Exception):
    """The check is being stopped, so nothing new is started."""


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def say(text: str):
    print(f"{now():%H:%M:%S} {text}", flush=True)


def git(*args: str) -> str | None:
    """What a git command prints, as it prints it, or None when it fails."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# Every process this check has running. Each is the leader of a process group of its own, so that
# stopping it stops what it started too: the build's compilers, the gate's runs.
LIVE: set[subprocess.Popen] = set()
LIVE_GUARD = threading.Lock()
ENDING = threading.Event()


def run_process(command: list[str], output, timeout: float | None = None, keep: tuple[int, ...] = ()) -> int | None:
    """Runs one command from the repository's root, its stdout and stderr going to the open file
    `output`. Gives its exit status, or None when it hadn't ended after `timeout` seconds and was
    stopped. `keep` are file descriptors it inherits: the lock, so that a run this check leaves
    behind still holds it."""
    with LIVE_GUARD:
        if ENDING.is_set():
            raise Ending
        process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True, pass_fds=keep)
        LIVE.add(process)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop(process)
        return None
    finally:
        with LIVE_GUARD:
            LIVE.discard(process)


def stop(process: subprocess.Popen):
    """Ends a process and everything it started: asks first, then doesn't ask."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=GRACE_SECONDS)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)  # what it started, if that outlived it
    except ProcessLookupError:
        pass
    process.wait()


def stop_everything():
    ENDING.set()
    with LIVE_GUARD:
        running = list(LIVE)
    for process in running:
        stop(process)


def run_captured(command: list[str], keep: tuple[int, ...] = ()) -> tuple[int | None, str]:
    """A short command's exit status and what it printed."""
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as output:
        status = run_process(command, output, keep=keep)
        output.seek(0)
        return status, output.read().rstrip("\n")


class Step:
    """One long command of the check: what was run, when, and how it ended. What it prints goes to
    `log`, a file in the sandbox."""

    def __init__(self, name: str, command: list[str], log: pathlib.Path, timeout: float):
        self.name, self.command, self.log, self.timeout = name, command, log, timeout
        self.started = self.ended = None
        self.status: int | None = None
        self.not_started: str | None = None

    def run(self, keep: tuple[int, ...]):
        self.started = now()
        try:
            with open(self.log, "w", encoding="utf-8") as output:
                self.status = run_process(self.command, output, self.timeout, keep)
        except OSError as error:  # not a program this machine can start
            self.not_started = error.strerror or str(error)
        self.ended = now()
        say(f"{self.name} ended: {self.how()}")

    def how(self) -> str:
        if self.not_started:
            return f"could not be started ({self.not_started})"
        if self.status is None:
            return f"stopped, because it hadn't ended after {self.timeout:.0f} s"
        return f"exit {self.status}"

    def when(self) -> str:
        return f"{self.started:%H:%M:%S} to {self.ended:%H:%M:%S} UTC, {self.how()}"

    def printed(self) -> list[str]:
        try:
            return self.log.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []


def run_together(steps: list[Step], jobs: int, keep: tuple[int, ...]):
    """Runs the steps `jobs` at a time, in the order given, and returns when all have ended."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=jobs)
    try:
        for future in [executor.submit(step.run, keep) for step in steps]:
            future.result()
    except BaseException:
        ENDING.set()
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    executor.shutdown()


class Plan(typing.NamedTuple):
    """What one check works on, each part read and checked before anything runs."""
    commit: str
    pin: str
    name: str  # the capture folder's name
    dest: pathlib.Path
    disc: pathlib.Path
    image: pathlib.Path  # the disc image the config names: what the program reads
    boot: pathlib.Path  # the boot file the config names: what the build translates
    before: pathlib.Path | None
    jobs: int
    cpus: int
    runs: dict[str, dict]
    tree: list[str]  # what the working tree held that the commit doesn't, before anything ran

    @property
    def label(self) -> str:
        """The gate's label for this check's capture."""
        return GATE_LABEL + self.name


def read_pin() -> str:
    """The pin file's hash, read as scripts/01_fetch_dream_recomp.sh reads it."""
    try:
        lines = (ROOT / PIN_FILE).read_text(encoding="utf-8").splitlines()
    except OSError as missing:
        raise CannotCheck(f"can't read {PIN_FILE}: {missing.strerror}") from missing
    pin = "".join(next((line for line in lines if not line.startswith("#")), "").split())
    if not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise CannotCheck(f"{PIN_FILE} must hold a full 40-digit hash, not '{pin}'")
    return pin


def scenario_of(name: str) -> str:
    """The gate's scenario for a baseline run that plays a recording back."""
    return name[:-len(REPLAY_SUFFIX)]


def seconds_of(run: dict) -> int:
    return run.get("max_seconds", compare_runs.DEFAULT_SECONDS)


def read_runs() -> dict[str, dict]:
    """The baseline's runs, each one checked to be a run this script knows how to make."""
    try:
        runs = compare_runs.read_baseline(ROOT / BASELINE)
    except compare_runs.CannotCompare as why:
        raise CannotCheck(str(why)) from why
    unsorted = compare_runs.DESCRIPTIONS ^ (HOW_A_RUN_IS_MADE | ABOUT_A_RUN)
    if unsorted:
        raise CannotCheck(f"{COMPARE} and this script disagree on what describes a baseline run: {', '.join(sorted(unsorted))}. "
                          "Put each in HOW_A_RUN_IS_MADE here, with the argument it becomes, or in ABOUT_A_RUN.")
    for name, run in runs.items():
        if not NAME.match(name):
            raise CannotCheck(f"{BASELINE}: the run {name!r} names its files, so its name is letters, digits, '_', '.' and '-'")
        seconds = seconds_of(run)
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise CannotCheck(f"{BASELINE}: {name}'s max_seconds is {seconds!r}, not a whole number of guest seconds")
        if not isinstance(run.get("press", ""), str):
            raise CannotCheck(f"{BASELINE}: {name}'s press is {run['press']!r}, not the text --press takes")
        recording = run.get("replay_input")
        if recording is None:
            continue
        if not isinstance(recording, str) or not (ROOT / recording).is_file():
            raise CannotCheck(f"{BASELINE}: {name}'s recording {recording!r} isn't a file of this checkout")
        if not name.endswith(REPLAY_SUFFIX) or name == REPLAY_SUFFIX:
            raise CannotCheck(f"{BASELINE}: {name} plays a recording back, and the gate's scenario is named from a "
                              f"run called NAME{REPLAY_SUFFIX}")
        if run.get("press") or not run.get("vmu"):
            raise CannotCheck(f"{BASELINE}: {name} plays a recording back, which the gate does on a new memory card "
                              "and with no presses. This script makes such a run through the gate alone, so it "
                              "can't make this one as its entry says.")
    return runs


def read_config() -> tuple[pathlib.Path, pathlib.Path]:
    """The disc image and the boot file the game's config names, each beside the config: what the
    program reads, and what the build translates."""
    try:
        with open(ROOT / CONFIG, "rb") as file:
            config = tomllib.load(file)
        image, boot = config["disc"]["image"], config["binary"]["path"]
        if not (isinstance(image, str) and isinstance(boot, str)):
            raise TypeError("each is the text of a path")
    except OSError as missing:
        raise CannotCheck(f"can't read {CONFIG}: {missing.strerror}") from missing
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as bad:
        raise CannotCheck(f"{CONFIG} doesn't name a disc image and a boot file ([disc] image and [binary] path): {bad}") from bad
    folder = (ROOT / CONFIG).parent
    return folder / image, folder / boot


def input_names() -> list[str]:
    """The file names of data/inputs.sha256, read as scripts/00_verify_inputs.sh reads them."""
    try:
        lines = (ROOT / INPUTS).read_text(encoding="utf-8").splitlines()
    except OSError as missing:
        raise CannotCheck(f"can't read {INPUTS}: {missing.strerror}") from missing
    return [line.partition(" ")[2].strip() for line in lines if line.strip() and not line.startswith("#")]


def distribution() -> str:
    try:
        return platform.freedesktop_os_release().get("PRETTY_NAME", "a distribution with no name")
    except OSError:
        return "a distribution with no os-release file"


def from_root(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def build_problems(pin: str) -> list[str]:
    """What keeps the build that is there from being this pin's: nothing, when there is a program,
    the gate's script, and a dream-recomp checkout at the pin with no change of its own."""
    problems = []
    program = ROOT / PROGRAM
    if not (program.is_file() and os.access(program, os.X_OK)):
        problems.append(f"there is no program at {PROGRAM}")
    if not (ROOT / GATE).is_file():
        problems.append(f"there is no {GATE}")
    if not (ROOT / DREAM / ".git").exists():
        problems.append(f"{DREAM} isn't a git checkout")
        return problems
    at = (git("-C", DREAM, "rev-parse", "HEAD") or "").strip()
    if at != pin:
        problems.append(f"{DREAM} is at {at or 'no commit'}, not at the pin {pin}")
    if git("-C", DREAM, "status", "--porcelain"):
        problems.append(f"{DREAM} has local changes, so what was built isn't the pin's code")
    return problems


def prepare(args: argparse.Namespace) -> Plan:
    """Reads and checks every input. Nothing is built, run or written before this returns."""
    runs = read_runs()
    pin = read_pin()
    commit = (git("rev-parse", "--verify", "--quiet", "HEAD^{commit}") or "").strip()
    if not commit:
        raise CannotCheck(f"{ROOT} isn't a git checkout with a commit, and the capture folder is named by the commit")
    tree = working_tree()
    if tree is None:
        raise CannotCheck("git can't say what this checkout's working tree holds (git status failed), and the capture "
                          "folder's manifest records what was built from")
    captures = pathlib.Path(args.captures).resolve()
    if not captures.is_dir():
        raise CannotCheck(f"{captures} isn't a folder: give the shared folder's captures/")
    if captures.is_relative_to(ROOT):
        raise CannotCheck(f"{captures} is inside this checkout, where what the check writes would be a change to the "
                          "working tree it records: give the shared folder's captures/")
    if args.label is not None and not NAME.match(args.label):
        raise CannotCheck(f"--label {args.label}: it names a folder, so it is letters, digits, '_', '.' and '-'")
    name = f"{commit[:7]}-{pin[:7]}" + (f"-{args.label}" if args.label else "")
    dest = captures / name
    if dest.exists():
        cut_short = f" Its {MARKER} says a check is running there, or was cut short." if (dest / MARKER).exists() else ""
        raise CannotCheck(f"{dest} is there already, and a capture folder is never written over.{cut_short} "
                          "Give this check a name of its own with --label NAME.")
    before = pathlib.Path(args.before).resolve() if args.before else None
    if before is not None and not (before.is_dir() and any(before.glob("*.hash"))):
        raise CannotCheck(f"--before {before} holds no gate capture (no *.hash file): give the gate/ folder of a capture folder")
    disc = args.disc or os.environ.get("JGR_DISC_DIR")
    if not disc:
        raise CannotCheck(f"no disc folder: give --disc FOLDER or set JGR_DISC_DIR. Every boot starts with {VERIFY}")
    if not pathlib.Path(disc).is_dir():
        raise CannotCheck(f"--disc {disc}: not a folder")
    image, boot = read_config()
    for path, what in ((image, "disc image"), (boot, "boot file")):
        if not path.is_file():
            raise CannotCheck(f"there is no {what} at {from_root(path)}, where {CONFIG} names it: make it first ({BUILDING})")
    cpus = len(os.sched_getaffinity(0))
    if args.jobs is not None and args.jobs < 1:
        raise CannotCheck(f"--jobs {args.jobs}: at least one thing runs at a time")
    # Half the CPUs is a cautious guess, not a measurement. On 9 November two gate captures and
    # eight runs overlapped in one sandbox, and no run was more than 6% under its baseline speed
    # (the shared folder's captures/2fa6456-6154c9a: its manifest's times and its reports). How many
    # went at a time there isn't recorded. A wrong guess costs time and no result: a run that
    # sharing slowed is made again alone.
    jobs = args.jobs if args.jobs is not None else max(1, cpus // 2)
    return Plan(commit, pin, name, dest, pathlib.Path(disc).resolve(), image, boot, before, jobs, cpus, runs, tree)


def take_lock():
    """One check at a time uses a checkout's build. The lock is a file in build/, held until this
    process and everything it started have ended."""
    path = ROOT / LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a", encoding="utf-8")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as held:
        handle.close()
        raise CannotCheck(f"another pin check, or a run that one left behind, is using this checkout's build ({LOCK} "
                          "is held). Wait for it to end: never start a build over a running one.") from held
    return handle


def run_command(name: str, run: dict, out: pathlib.Path, card: pathlib.Path) -> list[str]:
    """The program's arguments for one run of the baseline. `card` is a file that doesn't exist yet,
    so the program makes a blank, formatted card, as a player's first run does."""
    command = [str(ROOT / PROGRAM), "--config", str(ROOT / CONFIG), "--rtc-seed", "1",
               "--max-seconds", str(seconds_of(run))]
    if run.get("press"):
        command += ["--press", run["press"]]
    if run.get("replay_input"):
        command += ["--replay-input", str(ROOT / run["replay_input"])]
    if run.get("vmu"):
        command += ["--vmu", str(card)]
    return command + ["--report", str(out / f"{name}.report.txt"), "--write-hash", str(out / f"{name}.hash")]


def gate_capture_command(label: str, runs: dict[str, dict]) -> list[str]:
    """The build reference's capture command, with every recording of the baseline as a replay."""
    command = [sys.executable, str(ROOT / GATE), "capture", label, "--build", str(ROOT / BUILD),
               "--config", str(ROOT / CONFIG), "--game", GAME]
    for name, run in runs.items():
        if run.get("replay_input"):
            command += ["--replay", scenario_of(name), str(ROOT / run["replay_input"]), str(seconds_of(run))]
    return command


def speed_is_short(name: str, run: dict, report: pathlib.Path) -> bool:
    """Whether the compare script finds this run's speed more than its margin under the baseline's.
    Asked of that script's own comparison, with speed and without, so the two can't disagree."""
    fields = compare_runs.read_report(report.read_text(encoding="utf-8", errors="replace"))
    with_speed = compare_runs.compare(name, run, fields, compare_runs.SPEEDS["linux_sandbox"])[1]
    without = compare_runs.compare(name, run, fields, None)[1]
    return len(with_speed) > len(without)


def working_tree() -> list[str] | None:
    """What the working tree holds that HEAD doesn't, one line a file: git's two status letters, the
    file, and the SHA-256 of the file as it is. A pin move is checked before its commit exists, so
    this, read before the build, is what the commit made afterwards is held against: its copy of
    each file has that SHA-256, or the capture isn't of that commit. None when git can't say."""
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status is None:
        return None
    fields, lines = status.split("\0"), []
    while fields:
        entry = fields.pop(0)
        if not entry:
            continue
        letters, name = entry[:2], entry[3:]
        if "R" in letters or "C" in letters:
            fields.pop(0)  # the name it was renamed or copied from
        path = ROOT / name
        lines.append(f"{letters} {name}  " + (f"SHA-256 {sha256(path)}" if path.is_file() else "not a file in the working tree"))
    return lines


class Check:
    """One check as it goes: what it found, and the text of its evidence."""

    def __init__(self, plan: Plan, out: pathlib.Path, cards: pathlib.Path, keep: tuple[int, ...]):
        self.plan, self.out, self.cards, self.keep = plan, out, cards, keep
        self.logs = ROOT / LOGS / plan.name
        self.findings: list[str] = []
        self.commands: list[str] = []
        self.started = now()
        self.measured = False  # whether there is anything in `out` that took a build and the runs to make
        self.disc = "not checked"
        self.built = "not built"
        self.gate_result = "not captured"
        self.runs_result = "not made"

    def shown(self, command: list[str]) -> str:
        """A command as the manifest gives it, run from the repository's root: the script or program
        by its path from there, and this sandbox's folders named, not spelled out."""
        places = ((str(self.out), "$OUT"), (str(self.cards), "$CARDS"), (str(self.plan.disc), "$DISC"),
                  (sys.executable, "python3"), (str(ROOT), "$PWD"))
        words = []
        for at, word in enumerate(command):
            if at == 0 or (at == 1 and command[0] in (sys.executable, "bash")):
                word = word.removeprefix(str(ROOT) + os.sep)
            for path, name in places:
                word = word.replace(path, name)
            words.append(word if PLAIN_ARGUMENT.match(word) else shlex.quote(word))
        return " ".join(words)

    def ran(self, command: list[str]) -> str:
        self.commands.append(self.shown(command))
        return f"$ {self.commands[-1]}"

    def log_of(self, path: pathlib.Path) -> str:
        return f"the sandbox's {from_root(path)}"

    def verify_disc(self):
        """The disc and the boot file against data/inputs.sha256, then the disc image against the
        disc: nothing is built or run on a disc that wasn't checked."""
        plan = self.plan
        say(f"checking the disc with {VERIFY}")
        command = ["bash", str(ROOT / VERIFY), str(plan.disc), str(plan.boot)]
        status, printed = run_captured(command, self.keep)
        if status != 0:
            raise CannotCheck(f"the disc didn't pass {VERIFY}, so nothing was built or run:\n{printed}")
        self.ran(command)
        cues = [name for name in input_names() if name.lower().endswith(".cue")]
        if len(cues) != 1:
            raise CannotCheck(f"{INPUTS} names {len(cues)} .cue files, and the disc image is made from one")
        cue = (plan.disc / cues[0]).resolve()
        again = f'Make it again: python3 {MAKE_GDI} "{cue}" {from_root(plan.image)}'
        try:  # as scripts/02_make_gdi.py makes it, from the same folders
            expected = make_gdi.make_gdi(make_gdi.parse_cue(cue.read_text()), lambda track: (cue.parent / track).stat().st_size,
                                         make_gdi.track_folder(cue.parent, plan.image.resolve().parent))
            found = plan.image.read_text()
        except (OSError, ValueError) as bad:
            raise CannotCheck(f"can't hold {from_root(plan.image)} against the disc in {plan.disc}: {bad}. {again}") from bad
        if found != expected:
            raise CannotCheck(f"{from_root(plan.image)} isn't the disc image {MAKE_GDI} writes for the disc in {plan.disc}, "
                              f"so the program would read a disc that wasn't checked. {again}")
        self.disc = (f"checked by {VERIFY} against {INPUTS}, the boot file {from_root(plan.boot)} with it; "
                     f"{from_root(plan.image)} is the image {MAKE_GDI} writes for it")

    def build_step(self) -> Step:
        return Step("the build", ["bash", str(ROOT / BUILD_SCRIPT)], ROOT / BUILD_LOG, BUILD_LIMIT_SECONDS)

    def gate_step(self) -> Step:
        """The gate's capture, with the runs' limit for its own scenarios and its replays together."""
        runs = self.plan.runs
        seconds = GATE_OWN_GUEST_SECONDS + sum(seconds_of(run) for run in runs.values() if run.get("replay_input"))
        return Step("the gate's capture", gate_capture_command(self.plan.label, runs), self.logs / "gate-capture.txt",
                    seconds * HOST_SECONDS_A_GUEST_SECOND)

    def run_step(self, name: str, attempt: int) -> Step:
        """One run of the baseline, on a memory card of this attempt's own."""
        run = self.plan.runs[name]
        return Step(name, run_command(name, run, self.out / "runs", self.cards / f"{name}-{attempt}.card"),
                    self.logs / f"{name}-{attempt}.txt", seconds_of(run) * HOST_SECONDS_A_GUEST_SECOND)

    def build(self) -> bool:
        """Builds. False when there is no build of this pin to check."""
        say(f"building with {BUILD_SCRIPT}, about 15 minutes when there is something to build: its output is in {BUILD_LOG}")
        step = self.build_step()
        step.run(self.keep)
        self.commands.append(f"{self.shown(step.command)} > {BUILD_LOG} 2>&1")
        self.built = f"{BUILD_SCRIPT}, {step.when()}"
        problems = [f"{BUILD_SCRIPT}: {step.how()}"] if step.status != 0 else build_problems(self.plan.pin)
        if problems:
            self.findings.append(f"there is no build of this pin to check: {'; '.join(problems)}. The build's output "
                                 f"is in {self.log_of(step.log)}. Nothing was run.")
            return False
        self.built += f"; {PROGRAM} SHA-256 {sha256(ROOT / PROGRAM)}"
        return True

    def measure(self):
        """The gate's capture and every run of the baseline, then the two comparisons."""
        plan, runs_out = self.plan, self.out / "runs"
        shutil.rmtree(self.logs, ignore_errors=True)
        self.logs.mkdir(parents=True)
        store = ROOT / GATE_STORE
        for label in (plan.label, f"{plan.label}-before"):  # what a check of this name left there
            shutil.rmtree(store / label, ignore_errors=True)
        replays = {name: scenario_of(name) for name, run in plan.runs.items() if run.get("replay_input")}
        gate = self.gate_step()
        steps = {name: self.run_step(name, 1) for name in plan.runs if name not in replays}
        shared = plan.jobs > 1
        say(f"the gate's capture and {len(steps)} runs, {plan.jobs} at a time on {plan.cpus} CPUs")
        run_together([gate, *steps.values()], plan.jobs, self.keep)
        captured = sorted(path for pattern in GATE_FILES for path in (store / plan.label).glob(pattern))
        for path in captured:
            shutil.copy(path, self.out / "gate" / path.name)

        again: dict[str, Step] = {}
        for name, run in plan.runs.items():
            report = self.out / "gate" / f"{replays[name]}.report" if name in replays else runs_out / f"{name}.report.txt"
            ended_well = (gate if name in replays else steps[name]).status == 0
            if shared and ended_well and report.is_file() and speed_is_short(name, run, report):
                say(f"{name} was more than {compare_runs.SPEED_MARGIN:.0%} under the baseline's speed while it shared "
                    "the machine: making it again alone")
                if name not in replays:
                    for suffix in (".report.txt", ".hash"):
                        if (runs_out / f"{name}{suffix}").exists():
                            (runs_out / f"{name}{suffix}").rename(runs_out / f"{name}.shared{suffix}")
                again[name] = self.run_step(name, 2)
                again[name].run(self.keep)

        self.gate_evidence(gate, store, len(captured))
        self.runs_evidence(steps, again, replays, shared)
        self.measured = True

    def quoted(self, printed: list[str], own: re.Pattern, log: pathlib.Path) -> list[str]:
        """The gate's own result lines of what it printed, and a count of the rest."""
        lines = [line for line in printed if own.match(line)]
        rest = sum(1 for line in printed if line.strip()) - len(lines)
        if rest:
            lines.append(f"({rest} other line(s) it printed are in {self.log_of(log)}: they can hold a line the "
                         "program printed, which stays in the sandbox)")
        return lines or ["(no output)"]

    def gate_evidence(self, gate: Step, store: pathlib.Path, captured: int):
        plan = self.plan
        lines = [f"The regression gate on the build of commit {plan.commit[:7]} at pin {plan.pin[:7]}, by "
                 f"scripts/31_pin_check.py, {self.started:%-d %b %Y}. Commands run from the repository's root ($PWD).",
                 "", self.ran(gate.command), *self.quoted(gate.printed(), gate_capture_lines(plan.label), gate.log), gate.when()]
        if gate.status != 0 or not captured:
            self.gate_result = "the capture failed"
            self.findings.append(f"the gate's capture failed ({gate.how()}, {captured} file(s) captured), so the gate "
                                 f"says nothing about this build. What it printed is in {self.log_of(gate.log)}")
        elif plan.before is None:
            self.gate_result = f"captured, {captured} files, and compared with nothing (no --before)"
            lines += ["", "Not compared: no --before was given."]
        else:
            before, log = f"{plan.label}-before", self.logs / "gate-compare.txt"
            (store / before).mkdir(parents=True)
            for pattern in GATE_FILES:
                for path in plan.before.glob(pattern):
                    shutil.copy(path, store / before / path.name)
            command = [sys.executable, str(ROOT / GATE), "compare", before, plan.label]
            status, printed = run_captured(command, self.keep)
            log.write_text(printed + "\n", encoding="utf-8")
            said = self.quoted(printed.splitlines(), GATE_COMPARE_LINES, log)
            lines += ["", f"{before} is a copy of --before {plan.before}.", self.manifest_of(plan.before),
                      self.ran(command), *said, f"exit {status}"]
            if status == 0:
                self.gate_result = f"identical to --before {plan.before}"
            else:
                self.gate_result = f"DIFFERENT from --before {plan.before}"
                self.findings.append(f"the gate is not identical to --before {plan.before} (compare exit {status}):")
                self.findings += [f"  {line.strip()}" for line in said]
        lines += ["", "The gate measures guest writes only. It doesn't see drawing, sound or pacing.", f"Result: {self.gate_result}"]
        (self.out / "evidence/gate.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def manifest_of(before: pathlib.Path) -> str:
        """What the --before capture's own manifest says it was made from. Captures are compared
        only when made the same way, and that is the reader's to judge from these lines."""
        for manifest in (before / "MANIFEST.txt", before.parent / "MANIFEST.txt"):
            if manifest.is_file():
                text = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
                said = [line.strip() for line in text if re.match(r"\s*(commit|pin|clang|platform)\b", line, re.I)]
                return "\n".join([f"Its manifest, {manifest}, says:", *(f"  {line}" for line in said),
                                  "Captures are compared only when made the same way: that is the reader's to judge from those lines."])
        return "It has no MANIFEST.txt, in its folder or beside it, to say what it was made from."

    def runs_evidence(self, steps: dict[str, Step], again: dict[str, Step], replays: dict[str, str], shared: bool):
        plan, runs_out = self.plan, self.out / "runs"
        together = (f"while it shared the machine: the gate's capture and the {len(steps)} runs went {plan.jobs} at a time "
                    f"on {plan.cpus} CPUs") if shared else "with nothing else of this check running (--jobs 1)"
        lines = [f"The runs of {BASELINE} on the build of commit {plan.commit[:7]} at pin {plan.pin[:7]}, by "
                 f"scripts/31_pin_check.py, {self.started:%-d %b %Y}. Commands run from the repository's root ($PWD).",
                 "$OUT is the capture folder, and $CARDS a folder made new for the memory cards and deleted afterwards.", ""]
        pairs = []  # the reports the comparison takes from the gate
        for name in plan.runs:
            for step in filter(None, (steps.get(name), again.get(name))):
                if step.status != 0:
                    self.findings.append(f"{name}: the program didn't end as a run that reached its time limit does "
                                         f"({step.how()}). What it printed is in {self.log_of(step.log)}")
            lines.append(f"== {name}")
            if name in replays:
                lines += [f"Made by the gate's capture as its scenario {replays[name]} (evidence/gate.txt), with this run's own "
                          "arguments and --no-audio, which changes nothing in a run without a window. Its report is "
                          f"gate/{replays[name]}.report and its write hash gate/{replays[name]}.hash."]
            else:
                lines += [self.ran(steps[name].command), steps[name].when()]
            lines.append(f"Its speed was measured {together}.")
            if name in again:
                first = (f"gate/{replays[name]}.report", f"gate/{replays[name]}.hash") if name in replays else \
                    (f"runs/{name}.shared.report.txt", f"runs/{name}.shared.hash")
                lines += [f"That speed was more than {compare_runs.SPEED_MARGIN:.0%} under the baseline's, so the run was made "
                          "again alone, after everything else had ended, and the comparison below is of that one:",
                          self.ran(again[name].command), again[name].when(),
                          f"The first report and write hash are kept, {first[0]} and {first[1]}. "
                          + self.same_hash(name, self.out / first[1], runs_out / f"{name}.hash")]
            elif name in replays and (self.out / "gate" / f"{replays[name]}.report").is_file():
                pairs.append(f"{name}={self.out / 'gate' / (replays[name] + '.report')}")
            lines.append("")
        command = [sys.executable, str(ROOT / COMPARE), "--all", "--dir", str(runs_out), *pairs]
        status, printed = run_captured(command, self.keep)
        lines += ["== The comparison", self.ran(command), printed or "(no output)", f"exit {status}"]
        self.runs_result = printed.splitlines()[-1] if printed else f"{COMPARE} printed nothing (exit {status})"
        if status != 0:
            self.findings.append(f"the runs don't match the baseline ({COMPARE} exit {status}):")
            self.findings += [f"  {line}" for line in printed.splitlines() if line and not line.startswith("|")]
        (self.out / "evidence/ten-minute-runs.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def same_hash(self, name: str, first: pathlib.Path, second: pathlib.Path) -> str:
        """Holds the two write hashes of a run that was made twice against each other: with
        --rtc-seed 1, the same build repeats a run write for write."""
        if not (first.is_file() and second.is_file()):
            return "One of the two wrote no hash, so they weren't held against each other."
        if sha256(first) == sha256(second):
            return "The two write hashes are identical."
        self.findings.append(f"{name}: made twice on the same build, it wrote two different write hashes "
                             f"({first.relative_to(self.out).as_posix()} and {second.relative_to(self.out).as_posix()}), "
                             "where a run with --rtc-seed 1 repeats")
        return "The two write hashes DIFFER."

    def hold_tree(self):
        """The working tree once more, when everything has run. A file that changed meanwhile means
        the build, the runs and the comparison weren't all made from one tree."""
        before, after = self.plan.tree, working_tree()
        if after == before:
            return
        self.findings.append("the working tree changed while the check ran, so what was built, run and compared isn't "
                             "one tree. The manifest lists it as it was at the start. What differs:")
        if after is None:
            self.findings.append("  at the end: git status failed, so what it holds isn't known")
            return
        self.findings += [f"  at the start: {line}" for line in before if line not in after]
        self.findings += [f"  at the end: {line}" for line in after if line not in before]

    def result(self) -> str:
        if self.findings:
            return f"NOT UNCHANGED: {len([line for line in self.findings if not line.startswith('  ')])} finding(s)"
        if self.plan.before:
            return "UNCHANGED: every run matches the baseline, and the gate is identical to --before"
        return ("RUNS MATCH, GATE NOT COMPARED: every run matches the baseline, and the gate was captured and "
                "compared with nothing (no --before)")

    def manifest(self, sums: dict[str, str]) -> str:
        plan = self.plan
        differs = plan.tree
        origin = (git("rev-parse", "--verify", "--quiet", "origin/main^{commit}") or "").strip()
        on = "which is origin/main" if origin == plan.commit else \
            f"which is not origin/main ({origin[:7]})" if origin else "and this checkout has no origin/main"
        # Where scripts/01_fetch_dream_recomp.sh fetched the pin's code from, when that wasn't the
        # repository's own: a clone's path or a URL, recorded without any name or password in it.
        fetched = re.sub(r"(?<=://)[^/@]*@", "", os.environ.get("DREAM_RECOMP_URL", ""))
        clang = shutil.which("clang")
        version = subprocess.run([clang, "--version"], capture_output=True, text=True).stdout.splitlines()[:1] if clang else []
        scripts = sorted(path for path in (ROOT / "scripts").iterdir() if path.is_file())
        lines = [
            "Jet Set Recomp: a pin check, made by scripts/31_pin_check.py",
            f"commit: {plan.commit[:7]} ({plan.commit}), {on}",
            "working tree: " + (f"differs from the commit in {len(differs)} file(s), each with the SHA-256 of what was built from"
                                if differs else "as the commit has it"),
            *(f"  {line}" for line in differs),
            f"pin: {plan.pin} ({PIN_FILE}, as the working tree has it)"
            + (f", fetched from DREAM_RECOMP_URL={fetched}" if fetched else ""),
            f"clang: {version[0] if version else 'not found on PATH'}",
            f"date: {self.started:%-d %b %Y, %H:%M} to {now():%H:%M} UTC",
            f"platform: {platform.system()} {platform.release()} {platform.machine()}, {distribution()}, {plan.cpus} CPUs, "
            f"{plan.jobs} at a time",
            f"disc: {self.disc}",
            f"build: {self.built}",
            f"gate: {self.gate_result}",
            f"runs: {self.runs_result}",
            f"result: {self.result()}",
            *self.findings,
            "scripts/:",
            *(f"{sha256(path)}  scripts/{path.name}" for path in scripts),
            "commands, from the repository's root ($PWD). $OUT is this folder, $DISC the disc's, and $CARDS a folder",
            "made new for the memory cards and deleted afterwards:",
            *(f"  {command}" for command in self.commands),
            "files here:",
            *(f"{digest}  ./{name}" for name, digest in sums.items()),
        ]
        return "\n".join(lines) + "\n"

    def keep_capture(self) -> str:
        """Copies what was measured into the capture folder, each file read back and checked against
        its SHA-256, and takes the in-progress marker away. Says what it kept. `measured` is False
        once the folder holds it all, so that the sandbox's copy can go."""
        plan = self.plan
        sums = {path.relative_to(self.out).as_posix(): sha256(path)
                for path in sorted(self.out.rglob("*")) if path.is_file()}
        (self.out / "MANIFEST.txt").write_text(self.manifest(sums), encoding="utf-8")
        sums["MANIFEST.txt"] = sha256(self.out / "MANIFEST.txt")
        for name in sums:
            (plan.dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.out / name, plan.dest / name)
        wrong = [name for name, digest in sums.items() if sha256(plan.dest / name) != digest]
        if wrong:
            self.findings.append(f"{len(wrong)} file(s) of {plan.dest} don't have the SHA-256 they were written with: "
                                 f"{', '.join(wrong)}. The folder keeps its {MARKER}.")
            return f"{plan.dest}, with its {MARKER}: {len(wrong)} of its {len(sums)} files didn't read back as written"
        (plan.dest / MARKER).unlink()
        self.measured = False
        return f"{plan.dest}, {len(sums)} files, each read back and checked against its SHA-256"


def ended_from_outside(number: int, _frame):
    """SIGTERM, SIGHUP or SIGINT: the check is stopped, and main() below stops what it started."""
    print(f"31_pin_check.py: ended from outside ({signal.Signals(number).name}): stopping what it started",
          file=sys.stderr, flush=True)
    sys.exit(128 + number)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("captures", metavar="CAPTURES")
    parser.add_argument("--disc", metavar="FOLDER")
    parser.add_argument("--before", metavar="FOLDER")
    parser.add_argument("--jobs", metavar="N", type=int)
    parser.add_argument("--label", metavar="NAME")
    args = parser.parse_args(argv)
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(number, ended_from_outside)
    scratch = marker = check = None
    try:
        plan = prepare(args)
        lock = take_lock()
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="jgr-pin-check-"))
        out, cards = scratch / "out", scratch / "cards"
        for folder in (out / "gate", out / "runs", out / "evidence", cards):
            folder.mkdir(parents=True)
        check = Check(plan, out, cards, (lock.fileno(),))
        check.verify_disc()
        try:
            plan.dest.mkdir()
        except FileExistsError as taken:
            raise CannotCheck(f"{plan.dest} was made by another check while this one read the disc") from taken
        marker = plan.dest / MARKER
        marker.write_text(f"A pin check by scripts/31_pin_check.py started here at {check.started:%H:%M} UTC on "
                          f"{check.started:%-d %b %Y}, for commit {plan.commit[:7]} at pin {plan.pin[:7]}. It writes this "
                          "folder when it ends, and takes this file away. If no check is running, this one was cut "
                          "short: the folder holds nothing else of it.\n", encoding="utf-8")
        if check.build():
            check.measure()
        check.hold_tree()
        kept = check.keep_capture()
        marker = None
    except CannotCheck as why:
        print(f"31_pin_check.py: {why}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"31_pin_check.py: stopped, because a file or a folder couldn't be read or written: {error}", file=sys.stderr)
        return 2
    except Exception:  # an error of this script's own is never taken for a result
        traceback.print_exc()
        print("31_pin_check.py: stopped by an error of its own, above. Nothing it printed is a result.", file=sys.stderr)
        return 2
    finally:
        stop_everything()
        try:
            if marker is not None and marker.exists():
                with open(marker, "a", encoding="utf-8") as file:
                    file.write(f"It was cut short at {now():%H:%M} UTC.\n")
        except OSError:
            pass  # the folder can't be written, which is what is being reported already
        if scratch is not None:
            shutil.rmtree(scratch / "cards", ignore_errors=True)  # a memory card never stays
            if check is not None and check.measured:
                # The capture folder couldn't be written whole: the measurements took a build and
                # the runs to make, so the sandbox's copy stays, and is named.
                print(f"31_pin_check.py: what was measured is still in {scratch / 'out'}, in this sandbox", file=sys.stderr)
            else:
                shutil.rmtree(scratch, ignore_errors=True)

    print(f"gate: {check.gate_result}")
    print(f"runs: {check.runs_result}")
    print(f"kept: {kept}")
    for line in check.findings:
        print(line)
    print(check.result())
    return 1 if check.findings else 0


if __name__ == "__main__":
    sys.exit(main())
