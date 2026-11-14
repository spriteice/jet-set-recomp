# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the repository's own scripts. They use made-up data and need no disc.

    python3 -m unittest discover -s tests
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_gdi = load("02_make_gdi")
audit = load("audit_repo")
check_docs = load("check_docs")
compare_runs = load("30_compare_runs")

SECTOR = make_gdi.SECTOR_SIZE
CUE = """REM SINGLE-DENSITY AREA
FILE "t1.bin" BINARY
  TRACK 01 MODE1/2352
    INDEX 01 00:00:00
FILE "t2.bin" BINARY
  TRACK 02 AUDIO
    INDEX 00 00:00:00
    INDEX 01 00:02:00
REM HIGH-DENSITY AREA
FILE "t3.bin" BINARY
  TRACK 03 MODE1/2352
    INDEX 01 00:00:00
"""
SIZES = {"t1.bin": 606 * SECTOR, "t2.bin": 676 * SECTOR, "t3.bin": 1000 * SECTOR}


class MakeGdi(unittest.TestCase):
    def test_a_redump_cue_gives_the_tested_layout(self):
        text = make_gdi.make_gdi(make_gdi.parse_cue(CUE), SIZES.__getitem__, "d/")
        self.assertEqual(text.splitlines(), [
            "3",
            '1 0 4 2352 "d/t1.bin" 0',
            '2 756 0 2352 "d/t2.bin" 352800',  # 606 sectors, then the 150-sector pregap skipped
            '3 45000 4 2352 "d/t3.bin" 0',
        ])

    def test_a_cue_with_no_tracks_is_refused(self):
        with self.assertRaises(ValueError):
            make_gdi.parse_cue("REM nothing here\n")

    def test_a_disc_under_the_gdis_folder_gets_relative_paths(self):
        folder = pathlib.Path("/g")
        self.assertEqual(make_gdi.track_folder(folder / "disc", folder), "disc/")
        self.assertEqual(make_gdi.track_folder(folder, folder), "")
        self.assertEqual(make_gdi.track_folder(pathlib.Path("/media/stick/jgr"), folder), "/media/stick/jgr/")

    def test_the_written_gdi_names_tracks_relative_to_itself(self):
        with tempfile.TemporaryDirectory() as folder:
            disc = pathlib.Path(folder, "disc")
            disc.mkdir()
            (disc / "game.cue").write_text(CUE)
            for name, size in SIZES.items():
                (disc / name).write_bytes(b"\0" * size)
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/02_make_gdi.py"),
                                     f"{folder}/disc/game.cue", f"{folder}/disc.gdi"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = pathlib.Path(folder, "disc.gdi").read_text().splitlines()
        self.assertEqual(lines[1], '1 0 4 2352 "disc/t1.bin" 0')
        self.assertNotIn(folder, lines[3])


class Audit(unittest.TestCase):
    def findings(self, name: str, content: bytes = b"text\n"):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return audit.audit_file(path, path.relative_to(root))

    def test_ordinary_text_is_clean(self):
        self.assertEqual(self.findings("docs/notes.md", b"fn_0c014070 at 0x0C014070, 35,977 frames\n"), [])

    def test_disc_and_built_files_are_found(self):
        for name in ("Track 1.bin", "game.cue", "disc.gdi", "games/jgr/boot/x.txt", "1ST_READ.BIN",
                     "jgr_boot.exe", "jgr_boot", "vmu-a1.bin", "shot.png", "gen/jgr.h"):
            self.assertNotEqual(self.findings(name), [], name)

    def test_binary_content_is_found(self):
        self.assertIn("binary content", self.findings("notes.txt", b"abc\0def"))

    def test_the_ubuntu_snapshot_server_is_found_outside_docs(self):
        server = "snapshot" + ".ubuntu.com"
        for name, text in (("setup.sh", f"curl https://{server}/ubuntu/20260101T000000Z\n"),
                           ("ci.yml", "run: sudo apt-get install --" + "snapshot 20260101T000000Z cmake\n"),
                           ("ubuntu.sources", "Types: deb\nSnapshot: 20260101T000000Z\n")):
            self.assertTrue(any("snapshot server" in item for item in self.findings(name, text.encode())), name)
        self.assertFalse(any("snapshot server" in item for item in self.findings("notes.md", server.encode())))
        self.assertFalse(any("snapshot server" in item for item in self.findings("a.sh", b"apt-get install cmake\n")))

    def test_a_session_link_is_found(self):
        link = ("https://" + "claude" + ".ai/code/abc").encode()
        self.assertIn("a Claude session link", self.findings("notes.md", link))

    def test_generated_code_is_found(self):
        # Both of the emitter's signatures: the resume body is static, the plain body isn't.
        resume = b"static void fn_0c014070" + b"__resume(Ctx& c, Memory& m, std::uint32_t resume_pc) {"
        plain = b"void fn_0c014070" + b"(Ctx& c, Memory& m) { fn_0c014070__resume(c, m, 0); }"
        for code in (resume, plain):
            self.assertIn("generated C++", self.findings("notes.cpp", code), code)

    def test_instruction_text_is_found(self):
        self.assertIn("instruction text", self.findings("trace.log", b"0c014070: 4f22 sts.l pr,@-r15\n"))

    def test_a_commit_message_is_checked_before_the_commit_exists(self):
        """The commit-msg hook checks the message the way the commit audit does, minus the identity
        and signature, which don't exist yet. Git's '#' comment lines are ignored."""
        link = "https://" + "claude" + ".ai/code/session_x"
        self.assertIn("a Claude session link in the message", audit.audit_message("Add notes\n\n" + link, []))
        self.assertEqual(audit.audit_message("Add notes\n\nCo-Authored-By: Someone <a@example.com>", []), [])
        self.assertEqual(audit.audit_message("Add notes\n# " + link, []), [])
        self.assertIn("a denied word in the message", audit.audit_message("Notes for Pat", ["pat"]))
        with tempfile.TemporaryDirectory() as folder:
            message = pathlib.Path(folder) / "COMMIT_EDITMSG"
            message.write_text("Add notes\n\n" + link + "\n")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_repo.py"), folder,
                                     "--message", str(message)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("NOT CLEAN", result.stdout)
            message.write_text("Add notes\n")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_repo.py"), folder,
                                     "--message", str(message)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_large_text_file_is_found(self):
        big = b"x\n" * (audit.MAX_TEXT_BYTES // 2 + 1)
        self.assertTrue(any("too big" in item for item in self.findings("big.md", big)))


def fake_checkout(folder: pathlib.Path) -> pathlib.Path:
    """A copy of this repo's scripts and packaging, with stand-ins for the build and dream-recomp."""
    root = folder / "repo"
    for part in ("scripts", "packaging", "games", "data"):
        shutil.copytree(ROOT / part, root / part)
    shutil.copy(ROOT / "LICENSE", root / "LICENSE")
    jgr_boot = root / "build/games/jgr/jgr_boot"
    jgr_boot.parent.mkdir(parents=True)
    # Stands in for the program: records that it ran, and its arguments.
    jgr_boot.write_text('#!/bin/sh\necho "$@" > ran.txt\n')
    jgr_boot.chmod(0o755)
    (folder / "prefix/lib").mkdir(parents=True)
    # Stands in for the library: holds one sound system's looked-up name, as a real one does.
    (folder / "prefix/lib/libSDL3.so.0").write_bytes(b"\0pw_init\0")
    dream = root / "third_party/dream-recomp"
    (dream / "tools/dcdisc/dcdisc").mkdir(parents=True)
    (dream / "tools/dcdisc/dcdisc/__init__.py").write_text("")
    (dream / "LICENSE").write_text("GPL-2.0\n")
    return root


class Package(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        root = fake_checkout(self.folder)
        self.out = self.folder / "package"
        env = dict(os.environ, DREAM_LINUX_PREFIX=str(self.folder / "prefix"))
        subprocess.run(["bash", str(root / "scripts/20_package.sh"), "linux", str(self.out)],
                       check=True, capture_output=True, env=env)

    def test_the_package_holds_what_its_launchers_use(self):
        for name in ("jgr_boot", "jgr.toml", "play.sh", "setup.sh", "copy-disc.sh", "README.txt",
                     "tools/02_make_gdi.py", "tools/03_get_boot_file.py", "tools/inputs.sha256",
                     "tools/dcdisc/__init__.py", "licences/LICENSE-jet-set-recomp.txt",
                     "licences/LICENSE-dream-recomp.txt"):
            self.assertTrue((self.out / name).exists(), name)

    def test_the_package_holds_nothing_from_the_disc(self):
        for name in ("disc.gdi", "boot", "disc"):
            self.assertFalse((self.out / name).exists(), name)

    def play(self):
        return subprocess.run(["sh", str(self.out / "play.sh")], capture_output=True, text=True,
                              env=dict(os.environ, JGR_NO_DIALOG="1"))

    def test_play_stops_and_says_why_before_setup(self):
        result = self.play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run setup first", result.stderr)
        self.assertIn("copy-disc.sh", result.stderr)  # the route on a handheld, where the disc is on a stick
        self.assertIn("Run setup first", (self.out / "logs/launcher.txt").read_text())
        self.assertFalse((self.out / "ran.txt").exists())

    def test_setup_bat_reads_the_cue_path_before_moving_into_its_folder(self):
        # There's no Windows here to run it: the line order is what makes a relative path mean what it did
        # where it was typed, as setup.sh does.
        lines = (ROOT / "packaging/setup.bat").read_text().splitlines()
        read = next(i for i, line in enumerate(lines) if line == 'set "cue=%~f1"')
        moved = next(i for i, line in enumerate(lines) if line.startswith("cd /d "))
        self.assertLess(read, moved)
        self.assertIn('02_make_gdi.py "%cue%"', "\n".join(lines))

    def test_play_runs_with_a_timestamped_log_after_setup(self):
        (self.out / "disc.gdi").write_text("")
        (self.out / "boot").mkdir()
        (self.out / "boot/1ST_READ.BIN").write_text("")
        self.assertEqual(self.play().returncode, 0)
        args = (self.out / "ran.txt").read_text()
        self.assertRegex(args, r"--report logs/run-\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.txt")
        self.assertTrue((self.out / "logs").is_dir())
        self.assertEqual(list((self.out / "logs").glob("stderr-*")), [])  # nothing printed, no file

    def test_play_keeps_what_the_program_prints_and_names_a_crash(self):
        # Game Mode has no terminal: the program's own last words (a Vulkan error before a crash, say)
        # are only seen if play.sh keeps them.
        (self.out / "disc.gdi").write_text("")
        (self.out / "boot").mkdir()
        (self.out / "boot/1ST_READ.BIN").write_text("")
        (self.out / "jgr_boot").write_text('#!/bin/sh\necho "vk: device lost" >&2\nkill -SEGV $$\n')
        result = self.play()
        self.assertEqual(result.returncode, 139, result.stderr)
        kept = list((self.out / "logs").glob("stderr-*.txt"))
        self.assertEqual(len(kept), 1)
        self.assertRegex(kept[0].name, r"^stderr-\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.txt$")
        # The program's words, then the shell's own note of the signal where it gives one (dash does).
        self.assertTrue(kept[0].read_text().startswith("vk: device lost\n"), kept[0].read_text())
        self.assertIn("vk: device lost", result.stderr)  # and shown where there is a terminal
        launcher = (self.out / "logs/launcher.txt").read_text()
        self.assertIn("exited with code 139, killed by signal 11", launcher)
        self.assertIn(f"logs/{kept[0].name}", launcher)


class WindowsPackage(unittest.TestCase):
    def test_the_windows_package_holds_its_launchers_and_the_recorder(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        root = fake_checkout(folder)
        program = root / "build-win/games/jgr/jgr_boot.exe"
        program.parent.mkdir(parents=True)
        program.write_text("")
        (folder / "win/bin").mkdir(parents=True)
        # Stands in for SDL3.dll: holds DirectSound's looked-up name, as a real one does.
        (folder / "win/bin/SDL3.dll").write_bytes(b"\0DirectSoundCreate8\0")
        out = folder / "package"
        subprocess.run(["bash", str(root / "scripts/20_package.sh"), "windows", str(out)], check=True,
                       capture_output=True, env=dict(os.environ, DREAM_WIN_PREFIX=str(folder / "win")))
        for name in ("jgr_boot.exe", "SDL3.dll", "play.bat", "setup.bat", "record.bat", "jgr.toml"):
            self.assertTrue((out / name).exists(), name)

    def test_record_bat_keeps_the_card_it_started_from(self):
        # There's no Windows here to run it: the lines say the start card is copied before the run, the
        # run plays on the other copy, and the clock is fixed, which is what a replay needs.
        lines = (ROOT / "packaging/record.bat").read_text().splitlines()
        start = next(i for i, line in enumerate(lines) if "-card-start.bin" in line and line.startswith("copy "))
        run = next(i for i, line in enumerate(lines) if line.startswith('"%~dp0jgr_boot.exe"'))
        self.assertLess(start, run)
        self.assertIn('--vmu "logs\\record-%JGR_RUN%-card.bin"', lines[run])
        self.assertIn("--rtc-seed 1", lines[run])
        self.assertIn('--record-input "logs\\record-%JGR_RUN%-input.txt"', lines[run])
        self.assertNotIn("vmu-a1.bin", lines[run])  # the player's own save is never played on here


class CopyDisc(unittest.TestCase):
    """copy-disc.sh puts the player's disc inside the package, so the folder is complete and can move."""

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        root = fake_checkout(self.folder)
        self.out = self.folder / "package"
        env = dict(os.environ, DREAM_LINUX_PREFIX=str(self.folder / "prefix"))
        subprocess.run(["bash", str(root / "scripts/20_package.sh"), "linux", str(self.out)],
                       check=True, capture_output=True, env=env)
        # A made-up disc on a stick, and a hash list that names it, since the real list names the real disc.
        self.stick = self.folder / "stick/Jet Grind Radio (USA)"
        self.stick.mkdir(parents=True)
        self.cue = self.stick / "game.cue"
        self.cue.write_text(CUE)
        lines = ["# made up for the test", f"{hashlib.sha256(CUE.encode()).hexdigest()}  game.cue"]
        for name, size in SIZES.items():
            data = name.encode() * (size // len(name))
            (self.stick / name).write_bytes(data)
            lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
        lines.append(f"{'0' * 64}  1ST_READ.BIN")
        (self.out / "tools/inputs.sha256").write_text("\n".join(lines) + "\n")
        # The boot-file tool reads a real disc image; this stand-in records the .gdi it was given.
        (self.out / "tools/03_get_boot_file.py").write_text(
            "import pathlib, sys\n"
            "out = pathlib.Path(sys.argv[2])\n"
            "out.parent.mkdir(exist_ok=True)\n"
            "out.write_text(sys.argv[1])\n")

    def copy(self, cue: str, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None):
        return subprocess.run(["sh", str(self.out / "copy-disc.sh"), cue], capture_output=True, text=True,
                              cwd=cwd, env=env)

    def test_the_disc_is_copied_in_and_the_gdi_points_inside_the_folder(self):
        result = self.copy(str(self.cue))
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("game.cue", "t1.bin", "t2.bin", "t3.bin"):
            self.assertEqual((self.out / "disc" / name).read_bytes(), (self.stick / name).read_bytes(), name)
        gdi = (self.out / "disc.gdi").read_text()
        self.assertIn('"disc/t1.bin"', gdi)
        self.assertNotIn(str(self.stick), gdi)
        self.assertEqual((self.out / "boot/1ST_READ.BIN").read_text(), "disc.gdi")
        self.assertIn("Run ./play.sh", result.stdout)

    def test_a_different_disc_is_refused_and_its_copies_removed(self):
        (self.stick / "t2.bin").write_bytes(b"x" * SIZES["t2.bin"])
        result = self.copy(str(self.cue))
        self.assertEqual(result.returncode, 1)
        self.assertIn("t2.bin", result.stdout + result.stderr)
        self.assertIn("MK-51058 V1.005", result.stderr)
        self.assertFalse((self.out / "disc.gdi").exists())
        self.assertFalse((self.out / "boot").exists())
        self.assertEqual(sorted(path.name for path in (self.out / "disc").iterdir()), [])

    def test_a_missing_track_is_named_before_anything_is_checked(self):
        (self.stick / "t3.bin").unlink()
        result = self.copy(str(self.cue))
        self.assertEqual(result.returncode, 1)
        self.assertIn("t3.bin", result.stderr)
        self.assertFalse((self.out / "disc.gdi").exists())
        # The copies made before the missing track are removed too.
        self.assertEqual(sorted(path.name for path in (self.out / "disc").iterdir()), [])

    def test_a_copy_that_fails_part_way_leaves_nothing_behind(self):
        # A full disk fails cp part-way through a track. This cp stand-in does that on the second track.
        bin_dir = self.folder / "bin"
        bin_dir.mkdir()
        (bin_dir / "cp").write_text(
            "#!/bin/sh\n"
            'case "$2" in *t2.bin) head -c 16 "$1" > "$2"; echo "cp: No space left on device" >&2; exit 1 ;; esac\n'
            f'exec "{shutil.which("cp")}" "$@"\n')
        (bin_dir / "cp").chmod(0o755)
        path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        result = self.copy(str(self.cue), env=dict(os.environ, PATH=path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Couldn't copy t2.bin", result.stderr)
        self.assertIn("removed", result.stderr)
        self.assertEqual(sorted(path.name for path in (self.out / "disc").iterdir()), [])
        self.assertFalse((self.out / "disc.gdi").exists())

    def test_a_missing_cue_is_named(self):
        result = self.copy(str(self.stick / "none.cue"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("No .cue at", result.stderr)
        self.assertFalse((self.out / "disc").exists())

    def test_a_relative_cue_path_means_what_it_did_where_it_was_typed(self):
        # The scripts cd into their folder first; a relative path from another folder has to survive that.
        relative = str(self.cue.relative_to(self.folder))
        result = self.copy(relative, cwd=self.folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"disc/t1.bin"', (self.out / "disc.gdi").read_text())

    def test_setup_takes_a_relative_cue_path_from_another_folder_too(self):
        relative = str(self.cue.relative_to(self.folder))
        result = subprocess.run(["sh", str(self.out / "setup.sh"), relative], capture_output=True, text=True,
                                cwd=self.folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        gdi = (self.out / "disc.gdi").read_text()
        self.assertIn(str(self.stick / "t1.bin"), gdi)  # the disc stays where it is, so the path is absolute
        self.assertFalse((self.out / "disc").exists())


class PackageRefusals(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.root = fake_checkout(self.folder)
        self.out = self.folder / "package"

    def package(self):
        env = dict(os.environ, DREAM_LINUX_PREFIX=str(self.folder / "prefix"))
        return subprocess.run(["bash", str(self.root / "scripts/20_package.sh"), "linux", str(self.out)],
                              capture_output=True, text=True, env=env)

    def test_a_folder_that_was_set_up_is_refused(self):
        self.out.mkdir()
        (self.out / "disc.gdi").write_text("")
        result = self.package()
        self.assertEqual(result.returncode, 1)
        self.assertIn("isn't empty", result.stderr)
        self.assertFalse((self.out / "jgr_boot").exists())

    def test_a_missing_build_is_named(self):
        (self.root / "build/games/jgr/jgr_boot").unlink()
        result = self.package()
        self.assertEqual(result.returncode, 1)
        self.assertIn("build it first", result.stderr)

    def test_a_library_with_no_sound_system_is_refused_before_anything_is_copied(self):
        # The library SDL3 builds without the ALSA, PulseAudio and PipeWire headers: it names the
        # systems in its hint text but looks nothing up in them (known bug 21).
        library = self.folder / "prefix/lib/libSDL3.so.0"
        library.write_bytes(b"\0pulseaudio\0dummy\0disk\0")
        result = self.package()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("no audio backend", result.stderr)
        self.assertIn(str(library), result.stderr)
        self.assertFalse(self.out.exists())


class CheckSdlAudio(unittest.TestCase):
    check = load("21_check_sdl_audio")

    def test_a_looked_up_name_proves_its_backend(self):
        self.assertEqual(self.check.backends(b"\0snd_pcm_open\0pw_init\0"), ["alsa", "pipewire"])
        self.assertEqual(self.check.backends(b"DirectSoundCreate8"), ["directsound"])

    def test_a_system_named_but_not_looked_up_proves_nothing(self):
        self.assertEqual(self.check.backends(b"\0alsa\0pulseaudio\0pipewire\0directsound\0"), [])

    def test_the_command_names_the_backends_or_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            library = pathlib.Path(folder, "libSDL3.so.0.2.24")
            library.write_bytes(b"\0pa_context_new\0")
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/21_check_sdl_audio.py"), str(library)],
                                    capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout), (0, "libSDL3.so.0.2.24: audio backends pulseaudio\n"))
            library.write_bytes(b"\0dummy\0")
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/21_check_sdl_audio.py"), str(library)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"{library} has no audio backend", result.stderr)
            self.assertIn("09_setup_sandbox.sh", result.stderr)
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/21_check_sdl_audio.py"), f"{folder}/none"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("not a file", result.stderr)


def run_report(run: dict, speed: float = 1.8, stop: str = "time limit", **changed) -> str:
    """A made-up run report with a baseline run's counts, in the lines dream-recomp's launcher prints
    (runtime/boot/boot_main.cpp, report_text), the ones nothing reads included. `changed` replaces a
    count by its baseline key, and None leaves its line out."""
    count = {**run, **changed}
    seconds = count.get("max_seconds", 600)
    lines = [f"stop: {stop}",
             f"guest: {seconds:.3f} s ({seconds * 200000000 + 475} cycles), {count['frames']} frames, pc 0x0c226238",
             f"host: {seconds / speed:.2f} s ({speed:.1f}x real time)",
             f"interrupts delivered: {count['interrupts']} (max nesting 1), traps: {count['traps']}",
             "task-switching RTEs: 0",
             "syscalls: flashrom=17 gdrom=97535 sysinfo=5",
             f"GD-ROM sectors read: {count['gdrom_sectors']}",
             f"PVR: 271038168 TA chunks, 17933 list inits, {count['renders']} renders ({count['renders']} done), "
             "17928 frame swaps, 0 texture words, 0 yuv words",
             "  opaque: 261 polygons, 0 sprites, 0 modvols, 7598 vertices, 1 ends"]
    if count.get("memory_card") is not None:
        lines.append(f"memory card: {count['memory_card']}")
    lines += ["maple: 35950 transfers, 143818 frames, 107850 to empty ports, 35949 pad polls",
              f"AICA: arm7 running at pc 0x0000093c, {count['sound_samples_total']} samples, 600761 FIQs; mixer: "
              f"9 key-ons, 2 channels active, {count['sound_samples_nonzero']} of {count['sound_samples_total']} "
              "samples non-zero, dsp running; SCPU sh4->arm 0, arm->sh4 0",
              f"untranslated call targets: {count['untranslated_call_targets']}"]
    lines += [f"  0x0c28ed{8 + at:x}a called from 0x0c01bd94" for at in range(count["untranslated_call_targets"])]
    if count.get("unmapped_accesses") is not None:
        lines.append(f"unmapped memory accesses: {count['unmapped_accesses']}")
    return "\n".join(lines) + "\n"


class CompareRuns(unittest.TestCase):
    """30_compare_runs.py against the real data/baseline.json, with reports made up from its own counts."""
    RUNS = json.loads((ROOT / "data/baseline.json").read_text())["runs"]

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)

    def report(self, name: str, **changed) -> str:
        """Writes the run's report into the folder, as --dir reads it, and gives RUN=REPORT for it."""
        path = self.folder / f"{name}.report.txt"
        path.write_text(run_report(self.RUNS[name], **changed))
        return f"{name}={path}"

    def compare(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(ROOT / "scripts/30_compare_runs.py"), *args],
                              capture_output=True, text=True)

    def test_reports_with_the_baselines_own_counts_match_it(self):
        for name in self.RUNS:
            self.report(name)
        result = self.compare("--dir", str(self.folder), "--all")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        table = result.stdout.splitlines()
        self.assertEqual(table[0], "| | " + " | ".join(self.RUNS) + " |")
        self.assertIn("| Frames | 35977 | 35977 | 35977 | 35977 | 79438 |", table)
        self.assertIn("| Result | equal | equal | equal | equal | equal |", table)
        self.assertEqual(table[-1], f"MATCH: {len(self.RUNS)} of {len(self.RUNS)} runs, every count equal to "
                                    "data/baseline.json, every compared speed within 15% of it")

    def test_a_report_from_the_windows_build_reads_the_same(self):
        """jgr_boot.exe ends each line of its report with CR LF, as the run logs from the PC show."""
        path = self.folder / "no_input_vmu.report.txt"
        path.write_bytes(run_report(self.RUNS["no_input_vmu"], speed=2.4).replace("\n", "\r\n").encode())
        self.assertEqual(self.RUNS["no_input_vmu"]["windows_pc_speed_x"], 2.4)
        result = self.compare("--speed", "windows_pc", f"no_input_vmu={path}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("| Stopped | time limit, 600.000 s |", result.stdout)
        self.assertIn("| Speed | 2.4x (baseline 2.4x) |", result.stdout)
        self.assertIn("| Result | equal |", result.stdout)

    def test_every_count_the_baseline_holds_is_compared(self):
        """Each one changed alone is a finding that names the run, the count, and both numbers."""
        counts = dict(compare_runs.COUNTS)
        self.assertEqual(set(counts) | compare_runs.DESCRIPTIONS | set(compare_runs.SPEEDS.values()),
                         set().union(*self.RUNS.values()), "a key of the baseline that the script doesn't know")
        run = self.RUNS["presses_vmu"]
        for key, title in counts.items():
            with self.subTest(key):
                other = "16 block reads, 0 block writes, 1 media-info reads, 1 screen writes" if key == "memory_card" \
                    else run[key] + 1
                result = self.compare(self.report("presses_vmu", **{key: other}))
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f"presses_vmu: {title.lower()} {other}, baseline {run[key]}", result.stdout)
                self.assertIn(f"| {title} | {other} (baseline {run[key]}) |", result.stdout)
                self.assertIn("| Result | DIFFERENT |", result.stdout)
                self.assertIn("DIFFERENT: ", result.stdout.splitlines()[-1])

    def test_a_speed_more_than_15_percent_under_the_baseline_is_found(self):
        self.assertEqual(self.RUNS["no_input"]["linux_sandbox_speed_x"], 1.6)
        result = self.compare(self.report("no_input", speed=1.4))  # 12.5% under: noise between sandboxes
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("| Speed | 1.4x (baseline 1.6x, 12.5% under) |", result.stdout)
        result = self.compare(self.report("no_input", speed=1.3))  # 18.8% under
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no_input: speed 1.3x is 18.8% under the baseline's 1.6x, more than the 15% margin", result.stdout)
        # Runs that shared the machine say nothing about speed: asked for, and said in the result.
        result = self.compare("--speed", "none", self.report("no_input", speed=0.9))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("note: no speed was compared (--speed none)", result.stdout)
        self.assertIn("no speed compared", result.stdout.splitlines()[-1])
        # A run the baseline has no speed for on that platform isn't compared, and the result says so.
        self.assertNotIn("windows_pc_speed_x", self.RUNS["no_input"])
        result = self.compare("--speed", "windows_pc", self.report("no_input", speed=0.9))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("note: no_input's speed wasn't compared: the baseline has no windows_pc_speed_x for it", result.stdout)

    def test_a_card_run_and_a_run_without_a_card_arent_taken_for_each_other(self):
        card = self.RUNS["no_input_vmu"]["memory_card"]
        result = self.compare(self.report("no_input", memory_card=card))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no_input: the report has a memory card line, and the baseline's run has none", result.stdout)
        result = self.compare(self.report("no_input_vmu", memory_card=None))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"no_input_vmu: the report has no line for memory card (baseline {card})", result.stdout)

    def test_a_run_that_stopped_early_or_was_cut_short_is_found(self):
        path = self.folder / "no_input.report.txt"
        path.write_text(run_report(self.RUNS["no_input"], stop="fault"))
        result = self.compare(f"no_input={path}")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('no_input: the report ran 600.000 s of guest time and stopped on "fault"', result.stdout)
        path.write_text(run_report(dict(self.RUNS["no_input"], max_seconds=300)))  # --max-seconds 300
        result = self.compare(f"no_input={path}")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no_input: the report ran 300.000 s of guest time", result.stdout)
        # A report cut off before its last line, and a file that is no report at all.
        result = self.compare(self.report("no_input", unmapped_accesses=None))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no_input: the report has no line for unmapped accesses (baseline 0)", result.stdout)
        path.write_text("Segmentation fault\n")
        result = self.compare(f"no_input={path}")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("| Frames | missing (baseline 35977) |", result.stdout)
        self.assertIn("no_input: the report has no guest line", result.stdout)
        self.assertIn("no_input: the report has no host line, so no speed", result.stdout)

    def test_untranslated_targets_are_listed_as_the_report_prints_them(self):
        result = self.compare(self.report("presses", untranslated_call_targets=2))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("presses: untranslated call targets 2, baseline 0", result.stdout)
        self.assertIn("presses:   0x0c28ed8a called from 0x0c01bd94", result.stdout)
        self.assertIn("presses:   0x0c28ed9a called from 0x0c01bd94", result.stdout)

    def test_a_run_with_no_report_is_said_and_is_a_finding_when_all_are_needed(self):
        result = self.compare(self.report("no_input"), self.report("presses"))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("note: not compared, no report given: no_input_vmu, presses_vmu, "
                      "tutorial_mission1_kogane_replay", result.stdout)
        self.assertIn("MATCH: 2 of 5 runs", result.stdout)
        result = self.compare("--all", "--dir", str(self.folder))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("presses_vmu: no report was given, and --all needs every run of the baseline", result.stdout)
        self.assertIn("DIFFERENT: 3 finding(s) in 2 of 5 runs", result.stdout)

    def test_what_cant_be_compared_stops_it_and_says_why(self):
        for args, why in ((["no_input=" + str(self.folder / "none.txt")], "can't read no_input's report"),
                          (["attract=" + self.report("no_input").split("=")[1]], "attract isn't a run of the baseline"),
                          ([self.report("no_input"), self.report("no_input")], "no_input was given twice"),
                          ([str(self.folder / "no_input.report.txt")], "give each report as RUN=REPORT"),
                          (["--dir", str(self.folder / "none")], "not a folder"),
                          (["--baseline", str(self.folder / "none.json"), self.report("no_input")], "can't read the baseline"),
                          ([], "no report was given")):
            with self.subTest(why):
                result = self.compare(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(why, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        # A count added to the baseline that the script can't read from a report would go uncompared
        # in silence, so it stops the script instead.
        baseline = self.folder / "baseline.json"
        baseline.write_text(json.dumps({"runs": {"no_input": dict(self.RUNS["no_input"], texture_words=0)}}))
        result = self.compare("--baseline", str(baseline), self.report("no_input"))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("the run no_input has texture_words, which this script doesn't know", result.stderr)


class BuildScripts(unittest.TestCase):
    def test_a_build_with_no_boot_file_stops_before_it_starts(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        root = fake_checkout(folder)
        shutil.rmtree(root / "games/jgr/boot", ignore_errors=True)
        for script in ("10_build_linux.sh", "11_build_windows.sh"):
            with self.subTest(script):
                result = subprocess.run(["bash", str(root / "scripts" / script)], capture_output=True,
                                        text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn("make it first", result.stderr)
                self.assertFalse((root / "build").joinpath("CMakeCache.txt").exists())


class AuditCommits(unittest.TestCase):
    def repo(self, author: str, message: str, signed: bool = True) -> pathlib.Path:
        """A repo with one commit. It's made unsigned, whatever this machine's git would do, and a
        signed one then gets a stand-in signature header: the audit checks that one is there, and
        GitHub checks whose it is."""
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        name, email = author.split(" <")
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email.rstrip(">"),
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email.rstrip(">"))
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "notes.md").write_text("text\n")
        subprocess.run(["git", "-C", str(root), "add", "notes.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "--no-gpg-sign", "-m", message], check=True, env=env)
        if signed:
            git = ["git", "-C", str(root)]
            raw = subprocess.run([*git, "cat-file", "commit", "HEAD"], capture_output=True, check=True).stdout
            headers, message_part = raw.split(b"\n\n", 1)
            headers += b"\ngpgsig -----BEGIN SSH SIGNATURE-----\n U1NIU0lH\n -----END SSH SIGNATURE-----"
            commit = subprocess.run([*git, "hash-object", "-t", "commit", "-w", "--stdin"],
                                    input=headers + b"\n\n" + message_part, capture_output=True, check=True).stdout
            subprocess.run([*git, "update-ref", "HEAD", commit.decode().strip()], check=True)
        return root

    def test_the_project_identity_is_clean(self):
        root = self.repo(audit.IDENTITY, "Add notes\n\nCo-Authored-By: Someone <a@example.com>")
        self.assertEqual(audit.audit_commits(root, "HEAD", []), [])

    def test_an_unsigned_commit_is_found(self):
        root = self.repo(audit.IDENTITY, "Add notes", signed=False)
        found = audit.audit_commits(root, "HEAD", [])
        self.assertEqual(len(found), 1, found)
        self.assertIn("not signed", found[0])

    def test_another_author_is_found(self):
        root = self.repo("Pat Example <pat@example.com>", "Add notes")
        found = audit.audit_commits(root, "HEAD", [])
        self.assertTrue(any("author is not" in item for item in found), found)
        self.assertTrue(any("committer is not" in item for item in found), found)

    def test_a_session_link_in_a_message_is_found(self):
        root = self.repo(audit.IDENTITY, "Add notes\n\nhttps://" + "claude" + ".ai/code/session_x")
        self.assertTrue(any("session link" in item for item in audit.audit_commits(root, "HEAD", [])))

    def test_a_denied_word_is_found_in_messages_and_files(self):
        root = self.repo(audit.IDENTITY, "Add notes for Pat")
        self.assertTrue(any("denied word" in item for item in audit.audit_commits(root, "HEAD", ["pat"])))
        self.assertEqual(audit.denied_words("patch the path", ["pat"]), [])
        path = root / "notes.md"
        path.write_text("Thanks, Pat.\n")
        self.assertIn("a denied word", audit.audit_file(path, pathlib.PurePath("notes.md"), ["Pat"]))



class AuditIndex(unittest.TestCase):
    """The file audit reads what git has staged, which is what the next commit holds, and every kind of
    entry the index can have: a file, a link, a submodule."""
    TRACE = b"0c014070: 4f22 sts.l pr,@-r15\n"  # instruction text, which never goes in the repo

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "notes.md").write_text("text\n")
        self.git("add", "notes.md")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True,
                              text=True).stdout

    def run_audit(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(ROOT / "scripts/audit_repo.py"), str(self.root)],
                              capture_output=True, text=True)

    def test_a_submodule_is_named_and_not_opened(self):
        # dream-recomp's third_party/libchdr: the index holds another repository's commit, and the
        # working tree a folder. The audit read that folder as a file and stopped with a traceback.
        (self.root / "lib").mkdir()
        self.git("update-index", "--add", "--cacheinfo", "160000,8e7b8bd32bc676b7e5c6b42fe7d2daca986c4a0d,lib")
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("note: lib is a submodule, so its files weren't audited here", result.stdout)
        self.assertIn("CLEAN", result.stdout)

    def test_a_link_is_audited_as_git_stores_it(self):
        # Git stores a link as the path it points to, so that path is what the repo holds: a link to
        # a folder read as a file stopped the audit, and a link out of the repo had the file at its
        # end audited as if it were committed.
        outside = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "trace.txt").write_bytes(self.TRACE)
        (self.root / "docs").mkdir()
        (self.root / "to-docs").symlink_to("docs")
        (self.root / "to-trace").symlink_to(outside / "trace.txt")
        self.git("add", "to-docs", "to-trace")
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CLEAN", result.stdout)
        # and the path itself is checked like any content
        (self.root / "to-session").symlink_to("claude" + ".ai/code/x")
        self.git("add", "to-session")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("to-session: a Claude session link", result.stdout)

    def test_what_is_staged_is_audited_not_the_working_tree(self):
        # Staged with instruction text, then cleaned in the working tree only: the commit would hold
        # the staged text, and the audit used to read the clean copy and pass it (git add -p, or an
        # edit after git add).
        notes = self.root / "notes.md"
        notes.write_bytes(self.TRACE)
        self.git("add", "notes.md")
        notes.write_text("text\n")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("notes.md: instruction text", result.stdout)
        # A file deleted from the working tree but still staged is still committed, and still read.
        notes.unlink()
        self.assertIn("notes.md: instruction text", self.run_audit().stdout)
        # And an edit that isn't staged isn't in the commit, so it isn't a finding.
        self.git("add", "notes.md")  # stages the deletion
        (self.root / "other.md").write_text("text\n")
        self.git("add", "other.md")
        (self.root / "other.md").write_bytes(self.TRACE)
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CheckDocs(unittest.TestCase):
    """The docs check follows each pointer in the documents to its target, in made-up documents."""
    PIN = "6154c9aa3a86c9310cdbacca67bdadeaf41fb9ac"

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        # The least a checkout holds for the check to pass: a document, and the pin in its three places.
        self.write("data/dream-recomp.pin", f"# The pinned commit.\n{self.PIN}\n")
        self.write("data/baseline.json", '{"built_from": "dream-recomp 6154c9aa3a86, this repo\'s pin"}\n')
        self.write("docs/status.md", "# Status\n\n## Now\n\n- **Pin:** `6154c9a` (`data/dream-recomp.pin`).\n")

    def write(self, name: str, text: str, root: pathlib.Path | None = None) -> pathlib.Path:
        path = (root or self.root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def check(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(ROOT / "scripts/check_docs.py"), str(self.root), *args],
                              capture_output=True, text=True)

    def git(self, *args: str, root: pathlib.Path | None = None) -> str:
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        return subprocess.run(["git", "-C", str(root or self.root), *args], capture_output=True, check=True,
                              text=True, env=env).stdout.strip()

    def test_this_repositorys_own_documents_pass(self):
        result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/check_docs.py"), str(ROOT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"OK: \d+ documents, \d+ links, \d+ section names")

    def test_made_up_documents_with_nothing_wrong_pass(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # The pin in the status is a hash too, and nothing here can say whose: it is counted, never passed.
        self.assertEqual(result.stdout.splitlines(), [
            "note: 1 hash(es) not checked (ROOT isn't a git checkout, --dream wasn't given): 6154c9a",
            "OK: 1 documents, 0 links, 0 section names, 0 of 1 hashes"])

    def test_a_link_to_a_file_that_isnt_tracked_is_found(self):
        self.write("README.md", "# Readme\n")
        self.write("docs/plan.md", "# Plan\n\n"
                   "[the status](status.md), [the readme](../README.md#licence), [the data](../data),\n"
                   "[a web page](https://example.com/gone.md), [a part](#part), [gone](history.md),\n"
                   "[outside](../../elsewhere.md), and `[a sample](sample.md)` in code.\n\n"
                   "```\n[fenced](fenced.md)\n```\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("docs/plan.md:4: the link to history.md names no tracked file (docs/history.md)", result.stdout)
        self.assertIn("docs/plan.md:5: the link to ../../elsewhere.md leaves the repository", result.stdout)
        self.assertIn("NOT OK: 2 finding(s) in 3 documents, 5 links", result.stdout)

    def test_a_quoted_section_name_names_a_heading_or_a_bold_opening(self):
        self.write("docs/rules.md", "# Rules\n\n## Before every commit\n\n## 4. The project\n\n"
                   "- **Divergence,** our commits that upstream doesn't have.\n\n"
                   "```sh\n# change, rebuild\n```\n\n## Phase 10\n")
        good = ('`docs/rules.md`, "Before every commit" and "Divergence"; [the rules](docs/rules.md),\n'
                '"Phase 10"; `docs/rules.md`, section 4; and `reviews/elsewhere.md`, "Anything".\n')
        self.write("CLAUDE.md", "# Start here\n\n" + good)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("note: 1 section name(s) not checked: their documents aren't tracked here", result.stdout)
        self.assertIn("4 section names", result.stdout)
        # The heading was renamed or moved away, and the pointer stayed: each form is found, with its line.
        self.write("CLAUDE.md", "# Start here\n\n" + good +
                   '`docs/rules.md`, "Before every commit" and "What\'s open".\n'  # line 5
                   '[the rules](docs/rules.md),\n  "Things that bite".\n'  # line 6, wrapped
                   '`docs/rules.md`, "Phase 1".\n'  # line 8: "Phase 10" is another section
                   '`docs/rules.md`, "change, rebuild".\n'  # line 9: a comment in a code block is no heading
                   "`docs/rules.md`, sections 4 and 5.\n")  # line 10
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for line, name in ((5, "What's open"), (6, "Things that bite"), (8, "Phase 1"), (9, "change, rebuild")):
            self.assertIn(f'CLAUDE.md:{line}: "{name}" is no heading of docs/rules.md', result.stdout)
        self.assertIn('CLAUDE.md:10: docs/rules.md has no heading that starts "5."', result.stdout)
        self.assertIn("NOT OK: 5 finding(s)", result.stdout)

    def test_the_pin_is_the_same_in_its_three_places(self):
        self.write("docs/status.md", "# Status\n\n- **Pin:** `71d5a66` (`data/dream-recomp.pin`).\n")
        self.write("data/baseline.json", '{"built_from": "dream-recomp 71d5a6639dd2, this repo\'s pin"}\n')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("docs/status.md:3: the Pin line says 71d5a66, and data/dream-recomp.pin holds 6154c9aa3a86",
                      result.stdout)
        self.assertIn("data/baseline.json: built_from names 71d5a6639dd2, and data/dream-recomp.pin holds 6154c9aa3a86",
                      result.stdout)
        self.write("data/baseline.json", "not json\n")
        self.assertIn("data/baseline.json: isn't the JSON object it should be", self.check().stdout)
        self.write("data/dream-recomp.pin", "6154c9a\n")
        self.assertIn("data/dream-recomp.pin: holds no full 40-digit hash", self.check().stdout)
        (self.root / "data/dream-recomp.pin").unlink()
        self.assertIn("data/dream-recomp.pin: not tracked", self.check().stdout)

    def test_a_status_file_over_its_size_is_found(self):
        status = (self.root / "docs/status.md").read_text()
        self.write("docs/status.md", status + "x" * (check_docs.STATUS_MAX_BYTES - len(status)))
        self.assertEqual(self.check().returncode, 0)
        self.write("docs/status.md", status + "x" * (check_docs.STATUS_MAX_BYTES - len(status) + 1))
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("docs/status.md: 8,001 bytes, over 8,000", result.stdout)

    def test_a_hash_that_is_no_commit_is_found_once_both_repositories_can_be_asked(self):
        dream = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, dream)
        for repo, message in ((self.root, "ours"), (dream, "theirs")):
            self.git("init", "-q", root=repo)
            self.git("commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", message, root=repo)
        ours, theirs = self.git("rev-parse", "HEAD"), self.git("rev-parse", "HEAD", root=dream)
        gone = next(word for word in ("1234567", "7654321") if not ours.startswith(word) and not theirs.startswith(word))
        # The pin is a dream-recomp commit, as it is in the real documents.
        self.write("data/dream-recomp.pin", theirs + "\n")
        self.write("data/baseline.json", json.dumps({"built_from": f"dream-recomp {theirs[:12]}, this repo's pin"}))
        self.write("docs/status.md", f"# Status\n\n- **Pin:** `{theirs[:7]}` (`data/dream-recomp.pin`).\n")
        self.write("docs/history.md", f"# History\n\nOurs `{ours[:7]}`, theirs `{theirs[:12]}`, the range\n"
                   f"`{theirs[:7]}..{theirs[:8]}`, libchdr's `8e7b8bd`, and `{gone}`.\n"
                   f"A file's SHA-1, not a commit: `{'0' * 40}`.\n\n```\ngit show abcdef0\n```\n")
        self.git("add", ".")
        # Without dream-recomp, a word that is no commit here may be one there: counted, not found.
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("note: 4 hash(es) not checked (--dream wasn't given)", result.stdout)
        self.assertIn("2 of 6 hashes", result.stdout)
        # With it, and its full history, the one that is a commit nowhere is found.
        result = self.check("--dream", str(dream))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"docs/history.md:4: `{gone}` is no commit here or in dream-recomp", result.stdout)
        self.assertIn("NOT OK: 1 finding(s)", result.stdout)
        # A shallow clone may only be missing the commit, so nothing is called wrong from it.
        self.git("commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", "second", root=dream)
        shallow = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, shallow)
        subprocess.run(["git", "clone", "-q", "--depth", "1", dream.as_uri(), str(shallow)], check=True)
        result = self.check("--dream", str(shallow))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hash(es) not checked (--dream is a shallow clone)", result.stdout)
        result = self.check("--dream", str(self.root / "docs"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a git checkout", result.stderr)

    def test_what_is_staged_is_checked_not_the_working_tree(self):
        self.git("init", "-q")
        plan = self.write("docs/plan.md", "# Plan\n\n[gone](history.md)\n")
        self.git("add", ".")
        plan.write_text("# Plan\n")  # corrected, and not staged: the commit would still hold the link
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("docs/plan.md:3: the link to history.md", result.stdout)
        self.git("add", ".")
        self.assertEqual(self.check().returncode, 0)
        # A file that exists and isn't tracked is no target either: the commit wouldn't hold it.
        self.write("docs/history.md", "# History\n")
        self.write("docs/plan.md", "# Plan\n\n[the history](history.md)\n")
        self.git("add", "docs/plan.md")
        self.assertIn("names no tracked file", self.check().stdout)

    def test_the_bug_list_and_its_files_must_agree(self):
        shared = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, shared)
        self.write("known-bugs.md", "# Known bugs\n\n| # | Bug | Where | Critical? | State |\n|---|---|---|---|---|\n"
                   "| [1](known-bugs/bug-001.md) | Shadows aren't drawn | renderer | Not decided | Open |\n"
                   "| [2](known-bugs/bug-002.md) | A build with no FMA drifts | Toolchain | No | Fixed |\n", shared)
        self.write("known-bugs/bug-001.md", "# Bug 1: Shadows aren't drawn\n\n## Bug\n", shared)
        self.write("known-bugs/bug-002.md", "# Bug 2: A build with no FMA drifts\n", shared)
        result = self.check("--shared", str(shared))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 bug lines", result.stdout)
        index = shared / "known-bugs.md"
        index.write_text(index.read_text() +
                         "| [3](known-bugs/bug-003.md) | A run stopped at frame 82 | emitter | Yes | Fixed |\n"
                         "| [4](known-bugs/bug-004.md) | It doesn't compile headless | runtime | No | Fixed |\n"
                         "| [5](known-bugs/bug-004.md) | Textures flicker to black | renderer | No | Open |\n")
        self.write("known-bugs/bug-002.md", "# Bug 2: A MinGW build drifts\n", shared)  # retitled in one place
        self.write("known-bugs/bug-004.md", "Notes with no title line\n", shared)
        self.write("known-bugs/bug-006.md", "# Bug 6: Depth is wrong between models\n", shared)  # no line
        self.write("known-bugs/notes.md", "stray\n", shared)
        result = self.check("--shared", str(shared))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for finding in ('known-bugs/bug-002.md:1: the title isn\'t its line\'s in known-bugs.md: '
                        '"A MinGW build drifts" here, "A build with no FMA drifts" there',
                        "known-bugs.md:7: bug 3 has no file known-bugs/bug-003.md",
                        'known-bugs/bug-004.md:1: the first line isn\'t "# Bug 4: ..."',
                        "known-bugs.md:9: bug 5 links known-bugs/bug-004.md, not known-bugs/bug-005.md",
                        "known-bugs/bug-006.md: has no line in known-bugs.md",
                        "known-bugs/notes.md: isn't named bug-NNN.md"):
            self.assertIn(finding, result.stdout)
        self.assertIn("NOT OK: 6 finding(s)", result.stdout)
        # A shared folder that can't be seen is said, never passed over.
        result = self.check("--shared", str(shared / "none"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("known-bugs.md: not found, so the bug list went unchecked", result.stdout)

    def test_a_folder_with_no_documents_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/check_docs.py"), folder],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("holds no Markdown file", result.stderr)


class GitSetup(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.repo = self.folder / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.global_config = self.folder / "gitconfig"
        self.global_config.write_text("")

    def setup(self, repo: pathlib.Path | None = None):
        env = dict(os.environ, HOME=str(self.folder), GIT_CONFIG_GLOBAL=str(self.global_config))
        return subprocess.run(["bash", str(ROOT / "scripts/08_git_setup.sh"), str(repo or self.repo)],
                              capture_output=True, text=True, env=env)

    def config(self, key: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), "config", "--local", "--get", key],
                              capture_output=True, text=True).stdout.strip()

    def test_it_sets_the_project_identity(self):
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(f"{self.config('user.name')} <{self.config('user.email')}>", audit.IDENTITY)

    def test_it_keeps_the_sandboxs_signing_and_says_so(self):
        self.global_config.write_text("[commit]\n\tgpgsign = true\n[user]\n\tsigningkey = /k.pub\n")
        subprocess.run(["git", "-C", str(self.repo), "config", "user.signingkey", "/old"], check=True)
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("signed by the sandbox", result.stdout)
        self.assertEqual(self.config("user.signingkey"), "")

    def test_it_says_when_commits_wont_be_signed(self):
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unverified", result.stderr)

    def test_it_fetches_the_latest_origin_main(self):
        """A clone can be behind the remote, so setup fetches main."""
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        origin = self.folder / "origin"
        subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", str(origin)], check=True)
        commit = ["git", "-C", str(origin), "commit", "-q", "--allow-empty", "--no-gpg-sign", "-m"]
        subprocess.run([*commit, "first"], check=True, env=env)
        clone = self.folder / "clone"
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
        subprocess.run([*commit, "second"], check=True, env=env)
        latest = subprocess.run(["git", "-C", str(origin), "rev-parse", "HEAD"], check=True,
                                capture_output=True, text=True).stdout.strip()
        result = self.setup(clone)
        self.assertEqual(result.returncode, 0, result.stderr)
        fetched = subprocess.run(["git", "-C", str(clone), "rev-parse", "origin/main"], check=True,
                                 capture_output=True, text=True).stdout.strip()
        self.assertEqual(fetched, latest)
        self.assertIn("origin/main is", result.stdout)


    def commit(self, repo: pathlib.Path, message: str) -> subprocess.CompletedProcess:
        name, email = audit.IDENTITY.rstrip(">").split(" <")
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
        return subprocess.run(["git", "-C", str(repo), "commit", "-q", "--no-gpg-sign", "--allow-empty",
                               "-m", message], capture_output=True, text=True, env=env)

    def test_it_installs_the_audit_as_commit_hooks(self):
        """In a clone of this repo, a commit with a forbidden file or a session link in its message is
        refused before it's made, so a leak is stopped before a push could publish it."""
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("runs at commit time", result.stdout)
        for hook in ("pre-commit", "commit-msg", "pre-push"):
            self.assertTrue(os.access(self.repo / ".git/hooks" / hook, os.X_OK), hook)
        git = ["git", "-C", str(self.repo)]
        (self.repo / "notes.md").write_text("fn_0c014070, 35,977 frames\n")
        subprocess.run([*git, "add", "notes.md"], check=True)
        clean = self.commit(self.repo, "Add notes")
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        (self.repo / "vmu-a1.bin").write_bytes(b"\0" * 16)
        subprocess.run([*git, "add", "vmu-a1.bin"], check=True)
        refused = self.commit(self.repo, "Add a card")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("NOT CLEAN", refused.stdout + refused.stderr)
        subprocess.run([*git, "rm", "-q", "--cached", "vmu-a1.bin"], check=True)
        refused = self.commit(self.repo, "Add notes\n\nhttps://" + "claude" + ".ai/code/session_x")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("session link", refused.stdout + refused.stderr)
        log = subprocess.run([*git, "log", "--format=%s"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(log.split(), ["Add", "notes"])

    def test_it_leaves_a_hook_that_isnt_ours_alone(self):
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("isn't ours", result.stderr)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 0\n")
        self.assertTrue((self.repo / ".git/hooks/commit-msg").exists())
        self.assertTrue((self.repo / ".git/hooks/pre-push").exists())

    def test_it_installs_no_hooks_where_the_audit_isnt(self):
        """A dream-recomp clone has its own checks and no audit_repo.py, so it gets no hooks."""
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / ".git/hooks/pre-commit").exists())
        self.assertNotIn("runs at commit time", result.stdout)


class PushCheck(unittest.TestCase):
    """The pre-push hook, as scripts/08_git_setup.sh installs it, on real pushes to a bare remote that
    stands in for GitHub."""
    SIGNATURE = b"\ngpgsig -----BEGIN SSH SIGNATURE-----\n U1NIU0lH\n -----END SSH SIGNATURE-----"

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.remote = self.folder / "remote.git"
        self.repo = self.folder / "repo"
        self.shared = self.folder / "shared"
        (self.shared / "release-prep").mkdir(parents=True)
        (self.folder / "gitconfig").write_text("")
        name, email = audit.IDENTITY.rstrip(">").split(" <")
        # Nothing of this machine's git setup, its denylist or its shared folder reaches the test.
        self.env = dict(os.environ, HOME=str(self.folder), GIT_CONFIG_GLOBAL=str(self.folder / "gitconfig"),
                        GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name,
                        GIT_COMMITTER_EMAIL=email, JGR_SHARED_FOLDER=str(self.shared), JGR_AUDIT_DENYLIST="")
        self.env.pop("JGR_RELEASE_PUSH", None)
        subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", "--bare", str(self.remote)], check=True)
        subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", str(self.repo)], check=True)
        self.git("remote", "add", "origin", str(self.remote))
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        setup = subprocess.run(["bash", str(ROOT / "scripts/08_git_setup.sh"), str(self.repo)],
                               capture_output=True, text=True, env=self.env)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        self.assertIn("the push check at push time", setup.stdout)
        self.assertTrue(os.access(self.repo / ".git/hooks/pre-push", os.X_OK))
        self.git("add", "scripts")
        self.first = self.commit("Add the scripts")

    def git(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True,
                              env=dict(self.env, **env))

    def commit(self, message: str, signed: bool = True, *args: str, **env: str) -> str:
        """A commit on the current branch, and its hash. It's made unsigned, and a signed one then gets
        a stand-in signature header, as in AuditCommits: the audit checks that one is there."""
        made = self.git("commit", "-q", "--no-gpg-sign", "--allow-empty", "-m", message, *args, **env)
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        if signed:
            raw = subprocess.run(["git", "-C", str(self.repo), "cat-file", "commit", "HEAD"],
                                 capture_output=True, check=True).stdout
            headers, body = raw.split(b"\n\n", 1)
            commit = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-t", "commit", "-w", "--stdin"],
                                    input=headers + self.SIGNATURE + b"\n\n" + body, capture_output=True,
                                    check=True).stdout.decode().strip()
            self.assertEqual(self.git("update-ref", "HEAD", commit).returncode, 0)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def on_remote(self, ref: str = "refs/heads/main") -> str:
        """The commit the remote has at ref, or '' when it has no such ref."""
        return subprocess.run(["git", "-C", str(self.remote), "rev-parse", "-q", "--verify", ref],
                              capture_output=True, text=True).stdout.strip()

    def test_a_signed_fast_forward_of_main_is_pushed(self):
        result = self.git("push", "origin", "main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("push check: 1 commit(s)", result.stdout + result.stderr)
        self.assertEqual(self.on_remote(), self.first)
        second = self.commit("Add nothing")
        third = self.commit("Add nothing again")
        result = self.git("push", "origin", "main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("push check: 2 commit(s)", result.stdout + result.stderr)
        self.assertNotEqual(second, third)
        self.assertEqual(self.on_remote(), third)

    def test_any_ref_but_main_is_refused(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        self.git("tag", "v0.1")
        for refspec, ref in (("main:claude/a-session-branch", "refs/heads/claude/a-session-branch"),
                             ("v0.1", "refs/tags/v0.1")):
            with self.subTest(refspec):
                result = self.git("push", "origin", refspec)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"push refused: {ref} isn't main. Only main is pushed", result.stderr)
                self.assertEqual(self.on_remote(ref), "")
        # One refused ref stops the whole push, main's part of it too.
        second = self.commit("Add nothing")
        result = self.git("push", "origin", "main", "main:claude/a-session-branch")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.on_remote(), self.first)
        self.assertNotEqual(self.on_remote(), second)

    def test_a_push_that_isnt_a_fast_forward_is_refused_even_when_forced(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        self.commit("Say it another way", True, "--amend")  # a different commit in the pushed one's place
        result = self.git("push", "--force", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("so this would change pushed history", result.stderr)
        self.assertEqual(self.on_remote(), self.first)
        result = self.git("push", "origin", ":main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push refused: this would delete main on the remote", result.stderr)
        self.assertEqual(self.on_remote(), self.first)

    def test_a_remote_that_moved_is_refused_with_what_to_do(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        other = self.folder / "other"
        subprocess.run(["git", "clone", "-q", str(self.remote), str(other)], check=True, env=self.env)
        subprocess.run(["git", "-C", str(other), "commit", "-q", "--no-gpg-sign", "--allow-empty", "-m", "Theirs"],
                       check=True, env=self.env)
        subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True, env=self.env)
        theirs = self.on_remote()
        self.commit("Ours")
        result = self.git("push", "--force", "origin", "main")  # this clone never fetched theirs
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"the remote's main is at {theirs[:7]}, which this clone doesn't have. Fetch origin main first",
                      result.stderr)
        self.assertEqual(self.on_remote(), theirs)

    def test_a_push_is_refused_while_a_release_is_under_way(self):
        marker = self.shared / "release-prep/RELEASE-IN-PROGRESS.md"
        marker.write_text("v0.1\n")
        result = self.git("push", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push refused: a release is under way", result.stderr)
        self.assertIn(str(marker), result.stderr)
        self.assertEqual(self.on_remote(), "")
        marker.unlink()
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        # A sandbox outside the project can't see the shared folder: said, and not a reason to refuse.
        self.commit("Add nothing")
        result = self.git("push", "origin", "main", JGR_SHARED_FOLDER=str(self.folder / "none"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("so whether a release is under way", result.stdout + result.stderr)

    def test_every_commit_it_would_publish_is_audited(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        unsigned = self.commit("Add nothing", signed=False)
        result = self.git("push", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{unsigned[:7]}: not signed", result.stderr)
        self.assertIn("push refused: the audit found 1 thing(s) in the 1 commit(s) this would publish", result.stderr)
        self.git("reset", "-q", "--hard", self.first)
        other = self.commit("Add nothing", True, GIT_AUTHOR_NAME="Pat Example", GIT_AUTHOR_EMAIL="pat@example.com")
        result = self.git("push", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{other[:7]}: author is not the project identity", result.stderr)
        self.git("reset", "-q", "--hard", self.first)
        link = "https://" + "claude" + ".ai/code/session_x"
        self.commit("Add nothing\n\n" + link, True, "--no-verify")  # past the commit-msg hook
        result = self.git("push", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("a Claude session link in the message", result.stderr)
        self.assertEqual(self.on_remote(), self.first)

    def test_a_file_committed_past_the_hooks_is_found_in_the_history_it_would_publish(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        (self.repo / "vmu-a1.bin").write_bytes(b"\0" * 16)
        self.git("add", "-f", "vmu-a1.bin")
        added = self.commit("Add a card", True, "--no-verify")  # the commit hooks didn't run
        self.git("rm", "-q", "vmu-a1.bin")
        self.commit("Remove the card")  # the tip is clean again, and the card is still in the history
        result = self.git("push", "origin", "main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{added[:7]}: vmu-a1.bin: a disc, binary, card or capture file type", result.stderr)
        self.assertIn("in the 2 commit(s) this would publish", result.stderr)
        self.assertEqual(self.on_remote(), self.first)

    def test_the_releases_own_push_goes_out_while_the_release_is_marked_and_carries_its_tag(self):
        self.assertEqual(self.git("push", "origin", "main").returncode, 0)
        marker = self.shared / "release-prep/RELEASE-IN-PROGRESS.md"
        release = self.commit("Release notes")
        self.git("tag", "v0.1")
        # Not without the release being marked first: step 0 of the checklist.
        result = self.git("push", "origin", "main", "v0.1", JGR_RELEASE_PUSH="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JGR_RELEASE_PUSH is set, and no release is marked", result.stderr)
        self.assertEqual(self.on_remote("refs/tags/v0.1"), "")
        marker.write_text("v0.1\n")
        result = self.git("push", "origin", "main", "v0.1", JGR_RELEASE_PUSH="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.on_remote(), self.on_remote("refs/tags/v0.1")), (release, release))
        # A published tag is never moved or deleted, and a branch that isn't main is still refused.
        self.commit("Fix the notes")
        self.git("tag", "-f", "v0.1")
        for refspec, why in (("v0.1", "the remote already has the tag v0.1"), (":v0.1", "this would delete the tag v0.1"),
                             ("main:release", "refs/heads/release isn't main")):
            with self.subTest(refspec):
                result = self.git("push", "--force", "origin", refspec, JGR_RELEASE_PUSH="1")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(why, result.stderr)
        self.assertEqual(self.on_remote("refs/tags/v0.1"), release)


class FetchDreamRecomp(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.root = self.folder / "repo"
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        (self.root / "data").mkdir()

    def upstream(self, name: str) -> tuple[pathlib.Path, str]:
        """A stand-in dream-recomp with one commit, and that commit's hash."""
        repo = self.folder / name
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", name],
                       check=True, env=env)
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
        return repo, head

    def fetch(self, url: pathlib.Path, pin: str):
        (self.root / "data/dream-recomp.pin").write_text(pin + "\n")
        return subprocess.run(["bash", str(self.root / "scripts/01_fetch_dream_recomp.sh")],
                              capture_output=True, text=True, env=dict(os.environ, DREAM_RECOMP_URL=str(url)))

    def test_a_later_url_is_followed_after_the_first_fetch(self):
        first, first_head = self.upstream("first")
        self.assertEqual(self.fetch(first, first_head).returncode, 0)
        second, second_head = self.upstream("second")
        result = self.fetch(second, second_head)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(second_head, result.stdout)


class SetupErrors(unittest.TestCase):
    """Setup is the player's first step, so its scripts say what's wrong instead of a traceback."""

    def test_setup_says_when_python_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            shutil.copy(ROOT / "packaging/setup.sh", folder)
            # A PATH with the one tool the script uses before Python, and no python3, stands in for a
            # machine without it. The shell is named by its path, so it isn't looked up there.
            (pathlib.Path(folder) / "bin").mkdir()
            os.symlink(shutil.which("dirname"), f"{folder}/bin/dirname")
            result = subprocess.run(["/bin/sh", f"{folder}/setup.sh", "game.cue"], capture_output=True, text=True,
                                    env={"PATH": f"{folder}/bin"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python 3 isn't installed", result.stderr)
        self.assertNotIn("not found", result.stderr)

    def run_script(self, name: str, *args: str, **env):
        return subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / name), *args],
                              capture_output=True, text=True, env=dict(os.environ, **env))

    def test_a_missing_cue_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_script("02_make_gdi.py", f"{folder}/none.cue", f"{folder}/disc.gdi")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No .cue at", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_missing_track_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            pathlib.Path(folder, "game.cue").write_text(CUE)
            result = self.run_script("02_make_gdi.py", f"{folder}/game.cue", f"{folder}/disc.gdi")
        self.assertEqual(result.returncode, 1)
        self.assertIn("t1.bin", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_missing_disc_reader_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_script("03_get_boot_file.py", f"{folder}/disc.gdi", f"{folder}/boot/1ST_READ.BIN",
                                     DCDISC_DIR=folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("dcdisc", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class ReviewPack(unittest.TestCase):
    """review_pack.py in a made-up checkout: this repository's tracked files, its tests swapped for one
    small test (the real ones would run this class again, inside itself), one signed commit, and a
    stand-in shellcheck, so the test needs none installed."""
    SMALL_TEST = "import unittest\n\n\nclass Small(unittest.TestCase):\n    def test_it_holds(self):\n        self.assertTrue({})\n"
    GIT_TEST = ("import pathlib\nimport subprocess\nimport tempfile\nimport unittest\n\n\n"
                "class Small(unittest.TestCase):\n    def test_it_makes_a_repository_of_its_own(self):\n"
                "        with tempfile.TemporaryDirectory() as folder:\n"
                "            pathlib.Path(folder, 'note.txt').write_text('a note')\n"
                "            for args in (['init', '-q'], ['add', 'note.txt']):\n"
                "                subprocess.run(['git', '-C', folder, *args], check=True, capture_output=True)\n")
    MESSAGE = "Add a note\n\nIt says what the note is for.\n\nCo-Authored-By: Someone <a@example.com>\n"

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.repo, self.pack = self.folder / "repo", self.folder / "packs/one"
        for entry in audit.tracked_files(ROOT):
            rel = entry.path.relative_to(ROOT)
            if rel.parts[0] != "tests" and entry.path.is_file():
                (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(entry.path, self.repo / rel)
        self.write("tests/test_small.py", self.SMALL_TEST.format("True"))
        (self.folder / "bin").mkdir()
        (self.folder / "gitconfig").write_text("")
        self.shellcheck("exit 0")
        name, email = audit.IDENTITY.rstrip(">").split(" <")
        self.env = dict(os.environ, HOME=str(self.folder), GIT_CONFIG_GLOBAL=str(self.folder / "gitconfig"),
                        GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name,
                        GIT_COMMITTER_EMAIL=email, JGR_AUDIT_DENYLIST="",
                        PATH=f"{self.folder / 'bin'}{os.pathsep}{os.environ['PATH']}")
        for name in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
            self.env.pop(name, None)
        self.git("-c", "init.defaultBranch=main", "init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "--no-gpg-sign", "-m", "The checkout")
        # A stand-in signature header, as in AuditCommits: the audit checks that one is there.
        raw = subprocess.run(["git", "-C", str(self.repo), "cat-file", "commit", "HEAD"], capture_output=True, check=True).stdout
        headers, body = raw.split(b"\n\n", 1)
        signed = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-t", "commit", "-w", "--stdin"],
                                input=headers + PushCheck.SIGNATURE + b"\n\n" + body, capture_output=True, check=True)
        self.git("update-ref", "HEAD", signed.stdout.decode().strip())
        self.message = self.write("../message.txt", self.MESSAGE)

    def write(self, name: str, text: str) -> pathlib.Path:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def shellcheck(self, body: str):
        """A stand-in shellcheck on PATH: it answers --version, and otherwise does what `body` says."""
        tool = self.folder / "bin/shellcheck"
        tool.write_text(f'#!/bin/sh\nif [ "$1" = --version ]; then printf "ShellCheck\\nversion: 0.0.1\\n"; exit 0; fi\n{body}\n')
        tool.chmod(0o755)

    def git(self, *args: str, **env: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True,
                              env=dict(self.env, **env)).stdout

    def make_pack(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.repo / "scripts/review_pack.py"), str(self.pack),
                               "--message", str(self.message), *args], capture_output=True, text=True,
                              env=dict(self.env, **env))

    def stage_a_note(self):
        self.write("docs/notes.md", "# Notes\n\nSee [the status](status.md).\n")
        self.write("scripts/99_note.sh", "#!/usr/bin/env bash\n# SPDX-License-Identifier: GPL-2.0-only\necho note\n")
        self.git("add", "docs/notes.md", "scripts/99_note.sh")

    def test_a_staged_change_gets_its_diff_its_message_its_documents_and_its_checks(self):
        self.stage_a_note()
        head, tree = self.git("rev-parse", "HEAD"), self.git("write-tree")
        result = self.make_pack()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"READY FOR REVIEW: 6 checks passed on the staged tree {tree[:7]}", result.stdout)
        self.assertEqual((self.pack / "commit.diff").read_text(), self.git("diff", "--cached"))
        self.assertEqual((self.pack / "COMMIT_MSG.txt").read_text(), self.MESSAGE)
        self.assertEqual((self.pack / "documents/docs/notes.md").read_text(), "# Notes\n\nSee [the status](status.md).\n")
        self.assertEqual([path.name for path in (self.pack / "documents").rglob("*") if path.is_file()], ["notes.md"])
        evidence = (self.pack / "evidence/repo-checks.txt").read_text()
        for line in (f"The staged tree is {tree.strip()}, a change against HEAD", "$ python3 scripts/audit_repo.py . --commits HEAD",
                     "$ python3 scripts/audit_repo.py . --message COMMIT_MSG.txt", "$ python3 scripts/check_docs.py .",
                     "Ran 1 test in", "== bash -n on the 11 shell scripts of the staged tree", "-> everything changed is staged"):
            self.assertIn(line, evidence)
        self.assertEqual(evidence.count("-> passed"), 6, evidence)
        review = (self.pack / "REVIEW.md").read_text()
        self.assertIn("# Jet Set Recomp: Add a note", review)
        self.assertIn(f"on `{head[:7]}`. The staged\ntree that was checked is `{tree[:7]}`", review)
        self.assertIn("| 1 | `git status`, the staged files, the audit | 2 file(s) staged. Audit CLEAN", review)
        self.assertIn("| 2 | The full diff | `commit.diff`: 2 files changed, 6 insertions(+) |", review)
        self.assertIn("| 3 | The commit message | `COMMIT_MSG.txt`; the message audit is CLEAN |", review)
        self.assertIn("| 5 | The documents whole | `documents/docs/notes.md` |", review)
        self.assertIn("| 6 | The checks for the tree | 1 tests pass; the docs check is OK; `bash -n` passes on 11 scripts; "
                      "shellcheck 0.0.1 passes on them |", review)
        self.assertEqual(review.count("(to write)"), 3)  # what it changes, check 4, and what is unverified
        # It made a pack, and nothing else: no commit, and the same staged tree.
        self.assertEqual((self.git("rev-parse", "HEAD"), self.git("write-tree")), (head, tree))

    def test_the_checks_run_on_what_is_staged_not_on_the_working_tree(self):
        self.stage_a_note()
        self.write("tests/test_small.py", self.SMALL_TEST.format("False"))
        self.git("add", "tests/test_small.py")
        self.write("tests/test_small.py", self.SMALL_TEST.format("True"))  # mended, and not staged
        result = self.make_pack()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NOT READY: 1 check(s) failed: tests", result.stderr)
        self.assertIn("**the tests FAIL** (`evidence/repo-checks.txt`)", (self.pack / "REVIEW.md").read_text())
        evidence = (self.pack / "evidence/repo-checks.txt").read_text()
        self.assertIn("FAIL: test_it_holds", evidence)
        self.assertIn("-> 1 line(s) are of files edited or added and not staged", evidence)
        # And the other way round: staged whole, then broken in the working tree: the test, the script
        # and the document, with a failing test and a broken script that were never added. None of that
        # is in the commit, so none of it counts, and none of it is in the pack.
        self.git("add", "tests/test_small.py")
        self.write("tests/test_small.py", self.SMALL_TEST.format("False"))
        self.write("tests/test_untracked.py", self.SMALL_TEST.format("False"))
        self.write("scripts/98_broken.sh", "if then fi (\n")
        self.write("scripts/99_note.sh", "if then fi (\n")
        self.write("docs/notes.md", "# Notes\n\nSee [the history](gone.md).\n")
        # This stand-in reads the scripts it is given, as shellcheck does, and fails on the broken one.
        self.shellcheck('for script in "$@"; do if grep -q "if then" "$script"; then echo "$script: SC1000"; exit 1; fi; done')
        (self.pack / "REVIEW.md").unlink()
        result = self.make_pack()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 tests pass", (self.pack / "REVIEW.md").read_text())
        self.assertEqual((self.pack / "documents/docs/notes.md").read_text(), "# Notes\n\nSee [the status](status.md).\n")
        self.assertEqual((self.pack / "commit.diff").read_text(), self.git("diff", "--cached"))
        self.assertNotIn("gone.md", (self.pack / "commit.diff").read_text())

    def test_a_check_that_fails_is_named_and_the_pack_is_written_all_the_same(self):
        self.stage_a_note()
        self.message.write_text("Add a note\n\nhttps://" + "claude" + ".ai/code/session_x\n")
        self.shellcheck('echo "SC2086: Double quote to prevent globbing"; exit 1')
        self.write("docs/notes.md", "# Notes\n\nSee [the history](gone.md).\n")
        # A script that bash can't read, and not the last one by name: every script is read.
        self.write("scripts/05_broken.sh", "if then fi (\n")
        self.git("add", "docs/notes.md", "scripts/05_broken.sh")
        result = self.make_pack()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NOT READY: 4 check(s) failed: message, docs, syntax, shellcheck", result.stderr)
        review = (self.pack / "REVIEW.md").read_text()
        for bad in ("**the message audit is NOT CLEAN**", "**the docs check is NOT OK**", "**`bash -n` FAILS**",
                    "**shellcheck FAILS or is not installed**"):
            self.assertIn(bad, review)
        evidence = (self.pack / "evidence/repo-checks.txt").read_text()
        self.assertIn("a Claude session link in the message", evidence)
        self.assertIn("docs/notes.md:3: the link to gone.md names no tracked file", evidence)
        self.assertIn("scripts/05_broken.sh: line 1: syntax error", evidence)
        self.assertIn("SC2086", evidence)
        self.assertEqual(evidence.count("-> FAILED"), 4, evidence)
        self.assertTrue((self.pack / "commit.diff").read_text())
        # A machine with no shellcheck at all says so, and that is never a pass. Its PATH here holds
        # git and bash alone, so the test is the same on a machine that has shellcheck.
        (self.folder / "bin/shellcheck").unlink()
        for tool in ("git", "bash"):
            (self.folder / "bin" / tool).symlink_to(shutil.which(tool))
        result = self.make_pack(PATH=str(self.folder / "bin"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NOT READY: 4 check(s) failed: message, docs, syntax, shellcheck", result.stderr)
        evidence = (self.pack / "evidence/repo-checks.txt").read_text()
        self.assertIn("could not run shellcheck", evidence)
        self.assertEqual(evidence.count("-> FAILED"), 4, evidence)

    def test_a_review_that_is_written_already_is_left_as_it_is(self):
        self.stage_a_note()
        self.assertEqual(self.make_pack().returncode, 0)
        review = self.pack / "REVIEW.md"
        review.write_text("# My review\n\nWritten by hand.\n")
        self.git("rm", "-q", "--cached", "docs/notes.md")  # the change no longer adds the document
        self.write("README.md", (self.repo / "README.md").read_text() + "\nOne more line.\n")
        self.git("add", "README.md")
        result = self.make_pack()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(review.read_text(), "# My review\n\nWritten by hand.\n")
        self.assertIn("is there already and was left as it is. Its checks today:", result.stdout)
        self.assertIn("  6: 1 tests pass", result.stdout)
        self.assertEqual((self.pack / "commit.diff").read_text(), self.git("diff", "--cached"))
        self.assertTrue((self.pack / "documents/README.md").is_file())
        self.assertFalse((self.pack / "documents/docs").exists())  # the last run's copy is gone with its change

    def test_a_proposal_that_stands_on_another_takes_that_one_as_its_base(self):
        self.stage_a_note()
        self.write("tests/test_small.py", self.GIT_TEST)  # as the real tests do: a repository of its own
        self.git("add", "tests/test_small.py")
        first = self.git("write-tree").strip()
        self.write("docs/more.md", "# More\n")
        self.git("add", "docs/more.md")
        second = self.git("write-tree").strip()
        result = self.make_pack("--base", first)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        diff = (self.pack / "commit.diff").read_text()
        self.assertIn("docs/more.md", diff)
        self.assertNotIn("docs/notes.md", diff)
        self.assertIn(f"on the tree `{first[:7]}`, a proposal that isn't committed yet", (self.pack / "REVIEW.md").read_text())
        # A caller that reads a tree into an index of its own gets a pack of that tree, and the tests'
        # own repositories don't write into that index.
        index = self.folder / "index"
        self.git("read-tree", first, GIT_INDEX_FILE=str(index))
        (self.pack / "REVIEW.md").unlink()
        result = self.make_pack(GIT_INDEX_FILE=str(index))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"on the staged tree {first[:7]}", result.stdout)
        self.assertIn("docs/notes.md", (self.pack / "commit.diff").read_text())
        self.assertNotIn("docs/more.md", (self.pack / "commit.diff").read_text())
        self.assertEqual(self.git("write-tree", GIT_INDEX_FILE=str(index)).strip(), first)
        self.assertEqual(self.git("write-tree").strip(), second)

    def test_the_review_says_whether_the_base_is_the_latest_origin_main(self):
        """Every commit starts from the latest origin/main (docs/project-instructions.md, section 2)."""
        self.stage_a_note()
        head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/remotes/origin/main", head)
        self.assertEqual(self.make_pack().returncode, 0)
        self.assertIn(f"on `{head[:7]}`, which is `origin/main`. The staged", (self.pack / "REVIEW.md").read_text())
        self.assertIn(f"origin/main is {head}.", (self.pack / "evidence/repo-checks.txt").read_text())
        # The remote moved on: a commit this checkout has fetched and doesn't stand on.
        newer = self.git("commit-tree", "-p", head, "-m", "Another thread's commit", "HEAD^{tree}").strip()
        self.git("update-ref", "refs/remotes/origin/main", newer)
        (self.pack / "REVIEW.md").unlink()
        self.assertEqual(self.make_pack().returncode, 0)
        self.assertIn(f"on `{head[:7]}`, which is not `origin/main`. The staged", (self.pack / "REVIEW.md").read_text())

    def test_the_docs_checks_own_options_reach_it(self):
        self.stage_a_note()
        (self.folder / "shared").mkdir()  # a shared folder with no bug list in it
        result = self.make_pack("--shared", str(self.folder / "shared"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NOT READY: 1 check(s) failed: docs", result.stderr)
        self.assertIn("known-bugs.md", (self.pack / "evidence/repo-checks.txt").read_text())
        result = self.make_pack("--dream", str(self.folder / "shared"))  # and a folder that is no clone
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("not a git checkout", (self.pack / "evidence/repo-checks.txt").read_text())

    def test_with_nothing_to_review_it_stops_and_says_why(self):
        result = self.make_pack()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("nothing is staged that differs from HEAD", result.stderr)
        self.assertFalse(self.pack.exists())
        self.stage_a_note()
        for args, why in ((["--base", "no-such-rev"], "--base no-such-rev names no commit or tree here"),):
            result = self.make_pack(*args)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn(why, result.stderr)
        # A folder that has documents of its own and isn't a pack keeps them: a pack's are replaced.
        mine = self.folder / "mine"
        (mine / "documents").mkdir(parents=True)
        (mine / "documents/letter.txt").write_text("kept\n")
        result = subprocess.run([sys.executable, str(self.repo / "scripts/review_pack.py"), str(mine), "--message",
                                 str(self.message)], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("has a documents folder and no commit.diff", result.stderr)
        self.assertEqual([path.name for path in mine.rglob("*")], ["documents", "letter.txt"])
        self.message.write_text("\n")
        result = self.make_pack()
        self.assertEqual(result.returncode, 2)
        self.assertIn("is empty", result.stderr)
        self.message.unlink()
        result = self.make_pack()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no commit message at", result.stderr)
        self.assertFalse(self.pack.exists())


# Stands in for the program, build/games/jgr/jgr_boot. It records each call, makes the memory card it
# is given and refuses one that is there, prints what the game itself would, and writes the report
# and the write hash that state/behaviour.json gives for this call, or the ready ones. A call's
# record appears whole or not at all, because the tests read the records while the program runs.
STANDIN_PROGRAM = r"""#!PYTHON
import json, os, pathlib, sys, time
STATE = pathlib.Path("STATE_FOLDER")
args = sys.argv[1:]
given = lambda flag: args[args.index(flag) + 1] if flag in args else None
report, write_hash, card = given("--report"), given("--write-hash"), given("--vmu")
key = pathlib.Path(report).name.split(".")[0]
written = STATE / "calls" / f"{key}.{os.getpid()}.written"
written.write_text(json.dumps({"args": args, "cwd": os.getcwd(), "pid": os.getpid()}))
attempt = 0
while True:
    try:
        os.link(written, STATE / "calls" / f"{key}.{attempt}.json")
        break
    except FileExistsError:
        attempt += 1
written.unlink()
plans = json.loads((STATE / "behaviour.json").read_text()).get(key, [{}])
plan = plans[min(attempt, len(plans) - 1)]
if card:
    if os.path.exists(card):
        print(f"{card} is not a memory card image", file=sys.stderr)
        sys.exit(2)
    pathlib.Path(card).write_bytes(b"a made-up card")
print("serial output (19 bytes):\nTHE GAME'S OWN TEXT", flush=True)
time.sleep(plan.get("sleep", 0))
if "write" in plan:
    pathlib.Path(plan["write"]).write_text("not a folder")
if "exit" in plan:
    print("fault: THE GAME'S OWN TEXT", file=sys.stderr)
    sys.exit(plan["exit"])
pathlib.Path(report).write_text(plan.get("report") or (STATE / "reports" / f"{key}.txt").read_text())
pathlib.Path(write_hash).write_text(plan.get("hash") or f"{key} 1\n{key} 2\n")
"""

# Stands in for dream-recomp's tools/regress/gate.py, with its commands, its files in
# .regress/LABEL/, its lines and its exit statuses, as that script has them at the pin 6154c9a.
STANDIN_GATE = r"""#!/usr/bin/env python3
import argparse, hashlib, pathlib, subprocess, sys
REPO = pathlib.Path(__file__).resolve().parents[2]
STORE = REPO / ".regress"
SCENARIOS = {"attract": (40, []), "gameplay": (40, ["--press", "start@300,start@600,a@900"])}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def scenarios_of(label):
    listed = STORE / label / "scenarios"
    return {line.strip() for line in listed.read_text().splitlines() if line.strip()} if listed.exists() else set(SCENARIOS)


def capture(a):
    exe = REPO / a.build / "games" / a.game / f"{a.game}_boot"
    if not exe.is_file():
        print(f"no launcher {a.game}_boot in {exe.parent} that this host can start", file=sys.stderr)
        return 2
    out = STORE / a.label
    out.mkdir(parents=True, exist_ok=True)
    scenarios = dict(SCENARIOS)
    for name, recording, seconds in a.replay:
        card = out / f"{name}.card.bin"
        card.unlink(missing_ok=True)
        scenarios[name] = (int(seconds), ["--replay-input", str(pathlib.Path(recording).resolve()), "--vmu", str(card)])
    (out / "scenarios").write_text("".join(f"{name}\n" for name in scenarios))
    for name, (seconds, extra) in scenarios.items():
        h, rep = out / f"{name}.hash", out / f"{name}.report"
        try:
            proc = subprocess.run([str(exe), "--config", str(REPO / a.config), "--no-audio", "--rtc-seed", "1",
                                   "--max-seconds", str(seconds), *extra, "--write-hash", str(h), "--report", str(rep)],
                                  capture_output=True, text=True, cwd=str(REPO))
        except OSError as e:
            print(f"  {a.label}/{name}: could not start {exe} -- {e}", file=sys.stderr)
            return 2
        if not h.exists() or h.stat().st_size == 0:
            tail = (proc.stderr or proc.stdout or "").strip().split("\n")[-1:]
            print(f"  {a.label}/{name}: NO OUTPUT -- {' '.join(tail)}", file=sys.stderr)
            return 2
        counters = "\n".join(line for line in rep.read_text().splitlines() if not line.startswith("host:"))
        (out / f"{name}.counters").write_text(counters)
        print(f"  {a.label:14} {name:9} frames={sum(1 for _ in h.open()):<6} writehash={digest(h)} "
              f"counters={hashlib.sha256(counters.encode()).hexdigest()[:16]}")
    return 0


def compare(a):
    bad = False
    names = scenarios_of(a.before) | scenarios_of(a.after)
    for name in [n for n in SCENARIOS if n in names] + sorted(n for n in names if n not in SCENARIOS):
        pa, pb = STORE / a.before / f"{name}.hash", STORE / a.after / f"{name}.hash"
        missing = [p for p in (pa, pb) if not p.exists()]
        for p in missing:
            print(f"  {name:9} MISSING {p.relative_to(REPO)} -- capture it before comparing", file=sys.stderr)
        if missing:
            bad = True
            continue
        ca, cb = pa.with_suffix(".counters"), pb.with_suffix(".counters")
        same = ca.exists() and cb.exists() and ca.read_text() == cb.read_text()
        if digest(pa) == digest(pb) and same:
            print(f"  {name:9} identical")
        else:
            bad = True
            print(f"  {name:9} CHANGED  writehash {digest(pa)} -> {digest(pb)}{'' if same else '   counters differ too'}")
    if bad:
        print("\n  A changed hash is a fact; whether it matters is a judgement. Understand it before continuing.",
              file=sys.stderr)
    return 1 if bad else 0


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
c = sub.add_parser("capture")
c.add_argument("label")
c.add_argument("--build", default="build")
c.add_argument("--config", default="games/crazytaxi/crazytaxi.toml")
c.add_argument("--game", default="crazytaxi")
c.add_argument("--replay", nargs=3, action="append", default=[])
d = sub.add_parser("compare")
d.add_argument("before")
d.add_argument("after")
a = ap.parse_args()
raise SystemExit(capture(a) if a.cmd == "capture" else compare(a))
"""

# Stands in for scripts/10_build_linux.sh: it prints what a build can print, fails or makes nothing
# when the test says so, and otherwise puts the stand-in program where the build puts the real one.
STANDIN_BUILD = """#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -eu
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "GENERATED CODE fn_0c014070"
if [ -e "$root/../build-fails" ]; then
    echo "ninja: build stopped: subcommand failed." >&2
    exit 1
fi
if [ -e "$root/../build-makes-nothing" ]; then
    exit 0
fi
mkdir -p "$root/build/games/jgr"
cp "$root/../jgr_boot" "$root/build/games/jgr/jgr_boot"
echo "built $root/build/games/jgr/jgr_boot"
"""


class PinCheck(unittest.TestCase):
    """31_pin_check.py in a made-up checkout: this repository's tracked files and its real baseline, one
    commit, a made-up disc with a hash list that names it, and stand-ins for the build, the program
    and dream-recomp's gate. The disc check, the disc image and the comparison are the real scripts."""
    RUNS = CompareRuns.RUNS
    REPLAY, SCENARIO = "tutorial_mission1_kogane_replay", "tutorial_mission1_kogane"
    GAME_TEXT, BUILD_TEXT = "THE GAME'S OWN TEXT", "GENERATED CODE"

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.repo, self.state, self.captures = self.folder / "repo", self.folder / "state", self.folder / "captures"
        for entry in audit.tracked_files(ROOT):
            rel = entry.path.relative_to(ROOT)
            if rel.parts[0] != "tests" and entry.path.is_file():
                (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(entry.path, self.repo / rel)
        for folder in (self.state / "calls", self.state / "reports", self.captures, self.folder / "tmp"):
            folder.mkdir(parents=True)
        (self.folder / "gitconfig").write_text("")
        self.env = dict(os.environ, HOME=str(self.folder), GIT_CONFIG_GLOBAL=str(self.folder / "gitconfig"),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@example.com", TMPDIR=str(self.folder / "tmp"))
        for name in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "JGR_DISC_DIR", "DREAM_RECOMP_URL"):
            self.env.pop(name, None)
        # A made-up disc, a made-up boot file, and a hash list that names them, as in CopyDisc.
        self.disc = self.folder / "disc/Jet Grind Radio (USA)"
        self.disc.mkdir(parents=True)
        (self.disc / "game.cue").write_text(CUE)
        lines = ["# made up for the test", f"{hashlib.sha256(CUE.encode()).hexdigest()}  game.cue"]
        for name, size in SIZES.items():
            data = name.encode() * (size // len(name))
            (self.disc / name).write_bytes(data)
            lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
        self.boot = self.repo / "games/jgr/boot/1ST_READ.BIN"
        self.boot.parent.mkdir()
        self.boot.write_bytes(b"a made-up boot file")
        lines.append(f"{hashlib.sha256(b'a made-up boot file').hexdigest()}  1ST_READ.BIN")
        (self.repo / "data/inputs.sha256").write_text("\n".join(lines) + "\n")
        self.gdi = self.repo / "games/jgr/disc.gdi"
        self.make_gdi(self.disc)
        # The stand-ins. The build's is a tracked file of the made-up checkout, as the real one is.
        (self.repo / "scripts/10_build_linux.sh").write_text(STANDIN_BUILD)
        program = self.folder / "jgr_boot"
        program.write_text(STANDIN_PROGRAM.replace("PYTHON", sys.executable).replace("STATE_FOLDER", str(self.state)))
        program.chmod(0o755)
        self.behave()
        for name, run in self.RUNS.items():
            self.ready(name, run_report(run, speed=run["linux_sandbox_speed_x"]))
        self.ready(self.SCENARIO, run_report(self.RUNS[self.REPLAY], speed=self.RUNS[self.REPLAY]["linux_sandbox_speed_x"]))
        for name in ("attract", "gameplay"):
            self.ready(name, run_report(dict(self.RUNS["no_input"], max_seconds=40, frames=2399)))
        self.pin = self.make_dream()
        (self.repo / "data/dream-recomp.pin").write_text(f"# made up for the test\n{self.pin}\n")
        self.git("-c", "init.defaultBranch=main", "init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "--no-gpg-sign", "-m", "The checkout")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.name = f"{self.commit[:7]}-{self.pin[:7]}"
        self.logs = self.repo / "build/pin-check-logs"

    def make_dream(self) -> str:
        """A stand-in dream-recomp where the build fetches the real one: a repository of its own with
        the gate's script, which ignores its captures as the real one does. Gives its commit."""
        dream = self.repo / "third_party/dream-recomp"
        (dream / "tools/regress").mkdir(parents=True)
        (dream / "tools/regress/gate.py").write_text(STANDIN_GATE)
        (dream / ".gitignore").write_text(".regress/\n")
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-gpg-sign", "-m", "A stand-in dream-recomp"]):
            subprocess.run(["git", "-C", str(dream), *args], check=True, capture_output=True, env=self.env)
        return subprocess.run(["git", "-C", str(dream), "rev-parse", "HEAD"], check=True, capture_output=True,
                              text=True, env=self.env).stdout.strip()

    def make_gdi(self, disc: pathlib.Path):
        subprocess.run([sys.executable, str(self.repo / "scripts/02_make_gdi.py"), str(disc / "game.cue"), str(self.gdi)],
                       check=True, capture_output=True)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True,
                              env=self.env).stdout

    def ready(self, key: str, report: str):
        """The report the stand-in program writes for a run, or for a scenario of the gate."""
        (self.state / "reports" / f"{key}.txt").write_text(report)

    def behave(self, **plans: list[dict]):
        """What the stand-in program does on each call for a run or a scenario, the last one repeated:
        `report` and `hash` to write, `exit` to end on without writing, `sleep` first, and `write`,
        a file to leave somewhere else."""
        (self.state / "behaviour.json").write_text(json.dumps(plans))

    def calls(self, key: str | None = None) -> list[dict]:
        """The stand-in program's calls for one run or scenario, in order, or all of them."""
        files = sorted((self.state / "calls").glob(f"{key}.*.json" if key else "*.json"), key=lambda path: int(path.name.split(".")[-2]))
        return [json.loads(path.read_text()) for path in files]

    def check(self, *args: str, disc: pathlib.Path | None = None, **env: str) -> subprocess.CompletedProcess:
        command = [sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(self.captures)]
        if "JGR_DISC_DIR" not in env:
            command += ["--disc", str(disc or self.disc)]
        return subprocess.run([*command, *args], capture_output=True, text=True, env=dict(self.env, **env))

    def files(self, folder: pathlib.Path) -> list[str]:
        return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file())

    def eventually(self, holds, otherwise: str):
        """Waits for what follows a kill by a moment: a process that was killed takes one to go, and
        gives up what it held as it goes. Fails after 10 seconds."""
        for _ in range(200):
            if holds():
                return
            time.sleep(0.05)
        self.fail(otherwise)

    def assert_nothing_ran(self, result: subprocess.CompletedProcess, why: str):
        """It stopped at its inputs: exit 2 with the reason on one line, and nothing built, run or kept."""
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(why, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / "build-linux.log").exists(), "it built")
        self.assertEqual(list(self.captures.iterdir()), [])
        self.assertEqual(list((self.folder / "tmp").iterdir()), [])

    def test_a_build_that_matches_is_measured_once_and_its_capture_folder_written(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dest = self.captures / self.name
        said = result.stdout.splitlines()
        # With nothing to compare the gate with, the result's first words say so.
        self.assertEqual(said[-1], "RUNS MATCH, GATE NOT COMPARED: every run matches the baseline, and the gate was "
                                   "captured and compared with nothing (no --before)")
        self.assertIn("runs: MATCH: 5 of 5 runs, every count equal to data/baseline.json, every compared speed within 15% of it", said)
        self.assertIn("gate: captured, 10 files, and compared with nothing (no --before)", said)
        self.assertIn(f"kept: {dest}, 21 files, each read back and checked against its SHA-256", said)
        gate = [f"gate/{name}" for name in ("scenarios", *(f"{scenario}.{kind}" for scenario in ("attract", "gameplay", self.SCENARIO)
                                                           for kind in ("hash", "report", "counters")))]
        runs = [f"runs/{name}.{kind}" for name in self.RUNS if name != self.REPLAY for kind in ("hash", "report.txt")]
        self.assertEqual(self.files(dest), sorted(["MANIFEST.txt", "evidence/gate.txt", "evidence/ten-minute-runs.txt", *gate, *runs]))

        # Each run is made as the build reference gives it, from the repository's root.
        config = ["--config", str(self.repo / "games/jgr/jgr.toml"), "--rtc-seed", "1", "--max-seconds", "600"]
        (call,) = self.calls("no_input")
        self.assertEqual(call["args"][:6], config)
        self.assertEqual(call["args"][6::2], ["--report", "--write-hash"])
        self.assertEqual(call["cwd"], str(self.repo))
        (call,) = self.calls("presses_vmu")
        self.assertEqual(call["args"][:9], [*config, "--press", self.RUNS["presses_vmu"]["press"], "--vmu"])
        self.assertEqual(call["args"][10::2], ["--report", "--write-hash"])
        # The recorded play-through is the gate's scenario, made once, on a new card.
        self.assertEqual(self.calls(self.REPLAY), [])
        (call,) = self.calls(self.SCENARIO)
        recording = str(self.repo / self.RUNS[self.REPLAY]["replay_input"])
        self.assertEqual(call["args"][:9], ["--config", str(self.repo / "games/jgr/jgr.toml"), "--no-audio", "--rtc-seed", "1",
                                            "--max-seconds", "1325", "--replay-input", recording])
        self.assertEqual(len(self.calls()), 7)

        # The manifest: what the build reference lists, and a digest of every file beside it.
        manifest = (dest / "MANIFEST.txt").read_text()
        cpus = len(os.sched_getaffinity(0))
        script = hashlib.sha256((self.repo / "scripts/31_pin_check.py").read_bytes()).hexdigest()
        for line in (f"commit: {self.commit[:7]} ({self.commit}), and this checkout has no origin/main",
                     "working tree: as the commit has it",
                     f"pin: {self.pin} (data/dream-recomp.pin, as the working tree has it)",
                     f", {cpus} CPUs, {max(1, cpus // 2)} at a time",
                     "disc: checked by scripts/00_verify_inputs.sh against data/inputs.sha256, the boot file "
                     "games/jgr/boot/1ST_READ.BIN with it; games/jgr/disc.gdi is the image scripts/02_make_gdi.py writes for it",
                     f"{script}  scripts/31_pin_check.py",
                     "  bash scripts/00_verify_inputs.sh $DISC $PWD/games/jgr/boot/1ST_READ.BIN",
                     "  bash scripts/10_build_linux.sh > build-linux.log 2>&1",
                     f"  python3 third_party/dream-recomp/tools/regress/gate.py capture pin-check-{self.name} --build $PWD/build "
                     f"--config $PWD/games/jgr/jgr.toml --game jgr --replay {self.SCENARIO} "
                     "$PWD/data/recordings/2026-11-08-tutorial-mission1-kogane.txt 1325",
                     "  build/games/jgr/jgr_boot --config $PWD/games/jgr/jgr.toml --rtc-seed 1 --max-seconds 600 "
                     "--vmu $CARDS/no_input_vmu-1.card --report $OUT/runs/no_input_vmu.report.txt --write-hash $OUT/runs/no_input_vmu.hash",
                     f"  python3 scripts/30_compare_runs.py --all --dir $OUT/runs {self.REPLAY}=$OUT/gate/{self.SCENARIO}.report",
                     f"result: {said[-1]}"):
            self.assertIn(line, manifest)
        for heading in ("clang: ", "date: ", "platform: Linux ", "build: scripts/10_build_linux.sh, "):
            self.assertIn("\n" + heading, manifest)
        self.assertEqual(manifest.count("  scripts/"), len(list((self.repo / "scripts").iterdir())))
        listed = dict(reversed(line.split("  ./")) for line in manifest.split("files here:\n")[1].splitlines())
        self.assertEqual(sorted(listed), [name for name in self.files(dest) if name != "MANIFEST.txt"])
        for name, digest in listed.items():
            self.assertEqual(hashlib.sha256((dest / name).read_bytes()).hexdigest(), digest, name)

        # The evidence quotes the gate's own lines and the comparison's table.
        evidence = (dest / "evidence/gate.txt").read_text()
        for scenario in ("attract", "gameplay", self.SCENARIO):
            self.assertRegex(evidence, rf"(?m)^  pin-check-{self.name}\s+{scenario}\s+frames=2 +writehash=[0-9a-f]{{16}} counters=[0-9a-f]{{16}}$")
        self.assertIn("Not compared: no --before was given.", evidence)
        evidence = (dest / "evidence/ten-minute-runs.txt").read_text()
        self.assertIn("| Frames | 35977 | 35977 | 35977 | 35977 | 79438 |", evidence)
        self.assertIn(f"== {self.REPLAY}\nMade by the gate's capture as its scenario {self.SCENARIO} (evidence/gate.txt)", evidence)
        self.assertIn("Its speed was measured ", evidence)

        # What the program and the build printed is in the sandbox and nowhere else, and so are the
        # cards: the gate's is in its own store, and the runs' are deleted with their folder.
        self.assertIn(self.GAME_TEXT, (self.logs / self.name / "no_input-1.txt").read_text())
        self.assertIn(self.BUILD_TEXT, (self.repo / "build-linux.log").read_text())
        for text in (result.stdout, result.stderr, *((dest / name).read_text() for name in self.files(dest))):
            self.assertNotIn(self.GAME_TEXT, text)
            self.assertNotIn(self.BUILD_TEXT, text)
        self.assertTrue((self.repo / f"third_party/dream-recomp/.regress/pin-check-{self.name}/{self.SCENARIO}.card.bin").is_file())
        self.assertEqual(list((self.folder / "tmp").iterdir()), [])

        # The same build again, held against the first capture: unchanged, under a name of its own.
        # By then origin/main is another commit, which the manifest says.
        other = self.git("commit-tree", "HEAD^{tree}", "-m", "Another commit").strip()
        self.git("update-ref", "refs/remotes/origin/main", other)
        result = self.check("--before", str(dest / "gate"), "--label", "again")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "UNCHANGED: every run matches the baseline, and the gate is identical to --before")
        self.assertIn(f"commit: {self.commit[:7]} ({self.commit}), which is not origin/main ({other[:7]})\n",
                      (self.captures / f"{self.name}-again/MANIFEST.txt").read_text())
        evidence = (self.captures / f"{self.name}-again/evidence/gate.txt").read_text()
        for scenario in ("attract", "gameplay", self.SCENARIO):
            self.assertRegex(evidence, rf"(?m)^  {scenario}\s+identical$")
        self.assertIn(f"Its manifest, {dest / 'MANIFEST.txt'}, says:\n  commit: {self.commit[:7]}", evidence)
        self.assertIn(f"Result: identical to --before {dest / 'gate'}", evidence)

    def test_a_disc_that_wasnt_checked_stops_it_before_anything_is_built(self):
        # The same disc in another folder: it passes the hash list, and it isn't the one the image reads.
        other = self.folder / "other/Jet Grind Radio (USA)"
        shutil.copytree(self.disc, other)
        self.assert_nothing_ran(self.check(disc=other), "games/jgr/disc.gdi isn't the disc image scripts/02_make_gdi.py writes "
                                                         f"for the disc in {other}, so the program would read a disc that wasn't checked")
        # An image whose numbers aren't the checked disc's.
        self.gdi.write_text(self.gdi.read_text().replace(" 45000 ", " 45001 "))
        self.assert_nothing_ran(self.check(), "isn't the disc image scripts/02_make_gdi.py writes")
        self.make_gdi(self.disc)
        # A different release: one track's bytes, then the boot file's.
        track = (self.disc / "t2.bin").read_bytes()
        (self.disc / "t2.bin").write_bytes(b"x" * len(track))
        result = self.check()
        self.assert_nothing_ran(result, "the disc didn't pass scripts/00_verify_inputs.sh, so nothing was built or run")
        self.assertIn("MISMATCH  t2.bin", result.stderr)
        (self.disc / "t2.bin").write_bytes(track)
        self.boot.write_bytes(b"another release's boot file")
        self.assertIn("MISMATCH  1ST_READ.BIN", self.check().stderr)
        self.boot.write_bytes(b"a made-up boot file")
        # The boot file that is checked is the one the config names, wherever that is.
        config = self.repo / "games/jgr/jgr.toml"
        config.write_text(config.read_text().replace('path = "boot/1ST_READ.BIN"', 'path = "elsewhere/1ST_READ.BIN"'))
        (config.parent / "elsewhere").mkdir()
        (config.parent / "elsewhere/1ST_READ.BIN").write_bytes(b"another release's boot file")
        self.assertIn("MISMATCH  1ST_READ.BIN", self.check().stderr)
        self.git("checkout", "--", "games/jgr/jgr.toml")
        # A hash list that names no .cue: there is nothing to make the image from, or to hold it to.
        inputs = self.repo / "data/inputs.sha256"
        listed = inputs.read_text()
        inputs.write_text("".join(line + "\n" for line in listed.splitlines() if "game.cue" not in line))
        self.assert_nothing_ran(self.check(), "data/inputs.sha256 names 0 .cue files, and the disc image is made from one")
        inputs.write_text(listed)
        # Neither file made yet, which the hash list's check alone would pass over.
        self.boot.unlink()
        self.assert_nothing_ran(self.check(), "there is no boot file at games/jgr/boot/1ST_READ.BIN, where games/jgr/jgr.toml names it")
        self.boot.write_bytes(b"a made-up boot file")
        self.gdi.unlink()
        self.assert_nothing_ran(self.check(), "there is no disc image at games/jgr/disc.gdi, where games/jgr/jgr.toml names it")

    def test_a_count_that_differs_is_found_and_the_folder_is_kept_all_the_same(self):
        self.git("update-ref", "refs/remotes/origin/main", self.commit)
        self.behave(presses=[{"report": run_report(self.RUNS["presses"], frames=35978)}])
        result = self.check(JGR_DISC_DIR=str(self.disc), DREAM_RECOMP_URL="https://someone:a-password@example.com/dream-recomp")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        said = result.stdout.splitlines()
        self.assertIn("the runs don't match the baseline (scripts/30_compare_runs.py exit 1):", said)
        self.assertIn("  presses: frames 35978, baseline 35977", said)
        self.assertEqual(said[-1], "NOT UNCHANGED: 1 finding(s)")
        dest = self.captures / self.name
        self.assertIn("runs/presses.report.txt", self.files(dest))
        self.assertNotIn("IN-PROGRESS.txt", self.files(dest))
        manifest = (dest / "MANIFEST.txt").read_text()
        self.assertIn("result: NOT UNCHANGED: 1 finding(s)\nthe runs don't match the baseline (scripts/30_compare_runs.py exit 1):\n"
                      "  presses: frames 35978, baseline 35977\n", manifest)
        self.assertIn("| Frames | 35977 | 35978 (baseline 35977) | 35977 | 35977 | 79438 |", (dest / "evidence/ten-minute-runs.txt").read_text())
        # Where the commit and the pin's code came from is in the manifest, and no password with it.
        self.assertIn(f"commit: {self.commit[:7]} ({self.commit}), which is origin/main\n", manifest)
        self.assertIn(f"pin: {self.pin} (data/dream-recomp.pin, as the working tree has it), fetched from "
                      "DREAM_RECOMP_URL=https://example.com/dream-recomp\n", manifest)
        self.assertNotIn("a-password", manifest + result.stdout + result.stderr)

    def test_a_gate_that_changed_is_found(self):
        self.assertEqual(self.check().returncode, 0)
        before = self.captures / self.name / "gate"
        self.behave(gameplay=[{"hash": "another write\n"}])
        # What a check of this name left in the gate's store, cut short, is no part of this one.
        store = self.repo / "third_party/dream-recomp/.regress"
        for label, name in ((f"pin-check-{self.name}-after", "left.hash"), (f"pin-check-{self.name}-after-before", "gameplay.hash")):
            (store / label).mkdir()
            (store / label / name).write_text("left behind\n")
        result = self.check("--before", str(before), "--label", "after")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        said = result.stdout.splitlines()
        self.assertIn(f"gate: DIFFERENT from --before {before}", said)
        self.assertIn(f"the gate is not identical to --before {before} (compare exit 1):", said)
        self.assertRegex(result.stdout, r"(?m)^  gameplay +CHANGED  writehash [0-9a-f]{16} -> [0-9a-f]{16}$")
        self.assertRegex(result.stdout, r"(?m)^  attract +identical$")
        self.assertEqual(said[-1], "NOT UNCHANGED: 1 finding(s)")
        self.assertIn("MATCH: 5 of 5 runs", result.stdout)  # the runs are compared all the same
        self.assertNotIn("gate/left.hash", self.files(self.captures / f"{self.name}-after"))
        # A capture that lacks a scenario is never a match: an older one, made without the recording.
        self.behave()
        older = self.folder / "older"
        shutil.copytree(before, older)
        for path in older.glob(f"{self.SCENARIO}.*"):
            path.unlink()
        (older / "scenarios").write_text("attract\ngameplay\n")
        result = self.check("--before", str(older), "--label", "older")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertRegex(result.stdout, rf"(?m)^  {self.SCENARIO} +MISSING \S+ -- capture it before comparing$")
        self.assertIn("It has no MANIFEST.txt, in its folder or beside it, to say what it was made from.",
                      (self.captures / f"{self.name}-older/evidence/gate.txt").read_text())

    def test_a_run_that_was_slow_while_it_shared_the_machine_is_made_again_alone(self):
        slow, usual = run_report(self.RUNS["no_input"], speed=1.0), run_report(self.RUNS["no_input"], speed=1.6)
        replay = self.RUNS[self.REPLAY]
        self.ready(self.REPLAY, run_report(replay, speed=1.7))
        self.behave(**{"no_input": [{"report": slow}, {"report": usual}],
                       self.SCENARIO: [{"report": run_report(replay, speed=1.0), "hash": "the same writes\n"}],
                       self.REPLAY: [{"hash": "the same writes\n"}]})
        result = self.check("--jobs", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MATCH: 5 of 5 runs", result.stdout)
        dest = self.captures / self.name
        self.assertEqual(len(self.calls("no_input")), 2)
        self.assertEqual((dest / "runs/no_input.shared.report.txt").read_text(), slow)
        self.assertEqual((dest / "runs/no_input.report.txt").read_text(), usual)
        self.assertTrue((dest / "runs/no_input.shared.hash").is_file())
        self.assertEqual(len(self.calls("presses")), 1)  # within its margin: made once
        # The recorded play-through was the gate's, so alone it is made as the baseline's own run.
        (call,) = self.calls(self.REPLAY)
        self.assertEqual(call["args"][:8], ["--config", str(self.repo / "games/jgr/jgr.toml"), "--rtc-seed", "1", "--max-seconds",
                                            "1325", "--replay-input", str(self.repo / replay["replay_input"])])
        self.assertEqual(call["args"][8], "--vmu")
        evidence = (dest / "evidence/ten-minute-runs.txt").read_text()
        cpus = len(os.sched_getaffinity(0))
        self.assertIn(f"Its speed was measured while it shared the machine: the gate's capture and the 4 runs went 2 at a time on {cpus} CPUs.", evidence)
        self.assertIn("The first report and write hash are kept, runs/no_input.shared.report.txt and runs/no_input.shared.hash. "
                      "The two write hashes are identical.", evidence)
        self.assertIn(f"The first report and write hash are kept, gate/{self.SCENARIO}.report and gate/{self.SCENARIO}.hash. "
                      "The two write hashes are identical.", evidence)
        self.assertIn("| Speed | 1.6x (baseline 1.6x) |", evidence)
        self.assertIn("python3 scripts/30_compare_runs.py --all --dir $OUT/runs\n", evidence)

        # A run made twice on one build repeats write for write. Two hashes that differ are a finding.
        self.behave(**{self.SCENARIO: [{"report": run_report(replay, speed=1.0), "hash": "the same writes\n"}],
                       self.REPLAY: [{"hash": "other writes\n"}]})
        result = self.check("--jobs", "2", "--label", "twice")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"{self.REPLAY}: made twice on the same build, it wrote two different write hashes "
                      f"(gate/{self.SCENARIO}.hash and runs/{self.REPLAY}.hash), where a run with --rtc-seed 1 repeats", result.stdout)

        # Alone from the start, a slow run is a finding as it stands, and isn't made again.
        made = len(self.calls("no_input"))
        self.behave(no_input=[{"report": slow}])
        result = self.check("--jobs", "1", "--label", "alone")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("  no_input: speed 1.0x is 37.5% under the baseline's 1.6x, more than the 15% margin", result.stdout)
        self.assertEqual(len(self.calls("no_input")), made + 1)
        self.assertIn("Its speed was measured with nothing else of this check running (--jobs 1).",
                      (self.captures / f"{self.name}-alone/evidence/ten-minute-runs.txt").read_text())

    def test_a_capture_folder_that_is_there_is_never_written_over(self):
        self.assertEqual(self.check().returncode, 0)
        dest, made = self.captures / self.name, len(self.calls())
        kept = {name: (dest / name).read_bytes() for name in self.files(dest)}
        (self.repo / "build-linux.log").unlink()
        result = self.check()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(f"{dest} is there already, and a capture folder is never written over. Give this check a name "
                      "of its own with --label NAME.", result.stderr)
        self.assertEqual({name: (dest / name).read_bytes() for name in self.files(dest)}, kept)
        self.assertEqual(len(self.calls()), made)
        self.assertFalse((self.repo / "build-linux.log").exists())
        # A folder a check was cut short in says so, and is left as it is too.
        (self.captures / f"{self.name}-second").mkdir()
        (self.captures / f"{self.name}-second/IN-PROGRESS.txt").write_text("A pin check started here.\n")
        result = self.check("--label", "second")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Its IN-PROGRESS.txt says a check is running there, or was cut short.", result.stderr)
        self.assertEqual(self.files(self.captures / f"{self.name}-second"), ["IN-PROGRESS.txt"])
        result = self.check("--label", "third")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.files(self.captures / f"{self.name}-third"), sorted(kept))
        result = self.check("--label", "../elsewhere")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--label ../elsewhere: it names a folder", result.stderr)

    def test_without_a_build_of_the_pin_nothing_runs_and_the_folder_says_why(self):
        (self.folder / "build-fails").write_text("")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        said = result.stdout.splitlines()
        self.assertIn("there is no build of this pin to check: scripts/10_build_linux.sh: exit 1. The build's output is in "
                      "the sandbox's build-linux.log. Nothing was run.", said)
        self.assertEqual(said[-5:-3], ["gate: not captured", "runs: not made"])
        self.assertEqual(said[-1], "NOT UNCHANGED: 1 finding(s)")
        self.assertEqual(self.calls(), [])
        dest = self.captures / self.name
        self.assertEqual(self.files(dest), ["MANIFEST.txt"])
        self.assertIn("\nthere is no build of this pin to check: ", (dest / "MANIFEST.txt").read_text())
        self.assertNotIn(self.BUILD_TEXT, (dest / "MANIFEST.txt").read_text() + result.stdout + result.stderr)
        self.assertIn("ninja: build stopped", (self.repo / "build-linux.log").read_text())
        (self.folder / "build-fails").unlink()
        # A build that ends well and leaves no program is no build either.
        (self.folder / "build-makes-nothing").write_text("")
        result = self.check("--label", "nothing")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("there is no build of this pin to check: there is no program at build/games/jgr/jgr_boot. ", result.stdout)
        (self.folder / "build-makes-nothing").unlink()

        # A build that ends well beside a dream-recomp that isn't the pin's: local changes, then
        # another commit. The program there can't be called this pin's, so it isn't run.
        dream = self.repo / "third_party/dream-recomp"
        (dream / "tools/regress/note.txt").write_text("a change that isn't committed\n")
        result = self.check("--label", "changed")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("third_party/dream-recomp has local changes, so what was built isn't the pin's code", result.stdout)
        (dream / "tools/regress/note.txt").unlink()
        gate = (dream / "tools/regress/gate.py").read_text()
        (dream / "tools/regress/gate.py").unlink()
        result = self.check("--label", "no-gate")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("there is no third_party/dream-recomp/tools/regress/gate.py; ", result.stdout)
        (dream / "tools/regress/gate.py").write_text(gate)
        moved = "0123456789abcdef0123456789abcdef01234567"
        (self.repo / "data/dream-recomp.pin").write_text(f"# moved, and not committed\n{moved}\n")
        (self.repo / "docs/a note.md").write_text("not tracked\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"third_party/dream-recomp is at {self.pin}, not at the pin {moved}", result.stdout)
        self.assertEqual(self.calls(), [])
        # A pin that was moved and not committed: the folder is named by it, and the manifest says
        # what the working tree held that the commit doesn't, by its SHA-256.
        manifest = (self.captures / f"{self.commit[:7]}-{moved[:7]}/MANIFEST.txt").read_text()
        pin_file = hashlib.sha256((self.repo / "data/dream-recomp.pin").read_bytes()).hexdigest()
        note = hashlib.sha256(b"not tracked\n").hexdigest()
        self.assertIn("working tree: differs from the commit in 2 file(s), each with the SHA-256 of what was built from\n"
                      f"   M data/dream-recomp.pin  SHA-256 {pin_file}\n  ?? docs/a note.md  SHA-256 {note}\n"
                      f"pin: {moved} (data/dream-recomp.pin, as the working tree has it)\n", manifest)

    def test_a_run_that_doesnt_end_as_a_run_does_is_found(self):
        self.behave(presses_vmu=[{"exit": 1}])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        log = f"build/pin-check-logs/{self.name}/presses_vmu-1.txt"
        self.assertIn("presses_vmu: the program didn't end as a run that reached its time limit does (exit 1). What it "
                      f"printed is in the sandbox's {log}", result.stdout)
        self.assertIn("  presses_vmu: no report was given, and --all needs every run of the baseline", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], "NOT UNCHANGED: 2 finding(s)")
        self.assertIn(f"fault: {self.GAME_TEXT}", (self.repo / log).read_text())
        dest = self.captures / self.name
        self.assertIn("| Result | equal | equal | equal | equal |", (dest / "evidence/ten-minute-runs.txt").read_text())

        # A scenario of the gate that writes no hash: the gate prints the program's last line, and
        # that line stays in the sandbox. The gate's other scenarios aren't made, the play-through
        # among them, so that run has no report, and the four other runs are compared all the same.
        self.behave(gameplay=[{"exit": 1}])
        result = self.check("--label", "gate")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        log = f"build/pin-check-logs/{self.name}-gate/gate-capture.txt"
        self.assertIn(f"the gate's capture failed (exit 2, 4 file(s) captured), so the gate says nothing about this build. "
                      f"What it printed is in the sandbox's {log}", result.stdout)
        self.assertIn(f"  {self.REPLAY}: no report was given, and --all needs every run of the baseline", result.stdout)
        self.assertIn(f"NO OUTPUT -- fault: {self.GAME_TEXT}", (self.repo / log).read_text())
        dest = self.captures / f"{self.name}-gate"
        evidence = (dest / "evidence/gate.txt").read_text()
        self.assertRegex(evidence, rf"(?m)^  pin-check-{self.name}-gate +attract +frames=2 ")
        self.assertIn(f"(1 other line(s) it printed are in the sandbox's {log}: they can hold a line the program printed, "
                      "which stays in the sandbox)", evidence)
        for text in (result.stdout, result.stderr, *((dest / name).read_text() for name in self.files(dest))):
            self.assertNotIn(self.GAME_TEXT, text)
        self.assertIn("| Result | equal | equal | equal | equal |", (dest / "evidence/ten-minute-runs.txt").read_text())

        # A program this machine can't start is said too, for each run and by the gate.
        self.behave()
        (self.folder / "jgr_boot").write_text("#!/no/such/interpreter\n")
        result = self.check("--label", "no-program")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no_input: the program didn't end as a run that reached its time limit does (could not be started "
                      "(No such file or directory)).", result.stdout)
        self.assertIn("the gate's capture failed (exit 2, 1 file(s) captured)", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_file_of_the_checkout_that_changes_while_it_runs_is_found(self):
        # A file that isn't committed, as a moved pin isn't. While the runs go, something writes it again.
        note = self.repo / "docs/a note.md"
        note.write_text("as it was when the build was made\n")
        self.behave(no_input=[{"write": str(note)}])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        said = result.stdout.splitlines()
        start = "?? docs/a note.md  SHA-256 " + hashlib.sha256(b"as it was when the build was made\n").hexdigest()
        end = "?? docs/a note.md  SHA-256 " + hashlib.sha256(b"not a folder").hexdigest()
        at = said.index("the working tree changed while the check ran, so what was built, run and compared isn't one tree. "
                        "The manifest lists it as it was at the start. What differs:")
        self.assertEqual(said[at + 1:], [f"  at the start: {start}", f"  at the end: {end}", "NOT UNCHANGED: 1 finding(s)"])
        self.assertIn("MATCH: 5 of 5 runs", result.stdout)  # what was measured is kept and compared all the same
        manifest = (self.captures / self.name / "MANIFEST.txt").read_text()
        self.assertIn(f"working tree: differs from the commit in 1 file(s), each with the SHA-256 of what was built from\n  {start}\npin: ", manifest)
        self.assertIn("result: NOT UNCHANGED: 1 finding(s)\nthe working tree changed while the check ran", manifest)
        # A working tree git can no longer read once the runs have ended is said the same way.
        self.behave(no_input=[{"write": str(self.repo / ".git/index")}])
        result = self.check("--label", "unread")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines()[-2:], ["  at the end: git status failed, so what it holds isn't known",
                                                           "NOT UNCHANGED: 1 finding(s)"])

    def test_a_capture_folder_that_cant_be_written_whole_keeps_its_marker_and_loses_no_measurement(self):
        # While the runs go, a file appears where the capture folder's gate/ belongs.
        dest = self.captures / self.name
        self.behave(no_input=[{"write": str(dest / "gate")}])
        result = self.check()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("31_pin_check.py: stopped, because a file or a folder couldn't be read or written: ", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("UNCHANGED", result.stdout + result.stderr)
        self.assertNotIn("RUNS MATCH", result.stdout + result.stderr)
        self.assertRegex((dest / "IN-PROGRESS.txt").read_text(), r"It was cut short at \d\d:\d\d UTC\.\n\Z")
        # The build and the runs aren't made again for that: what they gave is named, and still there.
        (scratch,) = (self.folder / "tmp").iterdir()
        self.assertIn(f"31_pin_check.py: what was measured is still in {scratch / 'out'}, in this sandbox", result.stderr)
        self.assertIn("result: RUNS MATCH, GATE NOT COMPARED", (scratch / "out/MANIFEST.txt").read_text())
        self.assertTrue((scratch / "out/runs/presses_vmu.report.txt").is_file())
        self.assertFalse((scratch / "cards").exists())  # and the memory cards are gone all the same

        # A copy that doesn't read back as it was written is a finding, and the marker stays.
        pin_check = load("31_pin_check")
        out, kept = self.folder / "out", self.folder / "kept"
        (out / "runs").mkdir(parents=True)
        (out / "runs/no_input.hash").write_text("a write hash\n")
        kept.mkdir()
        (kept / "IN-PROGRESS.txt").write_text("A pin check started here.\n")
        plan = pin_check.Plan("c" * 40, "d" * 40, "ccccccc-ddddddd", kept, self.disc, self.gdi, self.boot, None, 1, 1, {}, [])
        check = pin_check.Check(plan, out, self.folder / "cards", ())
        check.measured = True

        def a_copy_that_loses_bytes(source, target):
            pathlib.Path(target).write_bytes(pathlib.Path(source).read_bytes()[:-1] if "hash" in str(source) else pathlib.Path(source).read_bytes())

        copyfile, pin_check.shutil.copyfile = pin_check.shutil.copyfile, a_copy_that_loses_bytes
        self.addCleanup(setattr, pin_check.shutil, "copyfile", copyfile)
        said = check.keep_capture()
        self.assertEqual(said, f"{kept}, with its IN-PROGRESS.txt: 1 of its 2 files didn't read back as written")
        self.assertEqual(check.findings, [f"1 file(s) of {kept} don't have the SHA-256 they were written with: runs/no_input.hash. "
                                          "The folder keeps its IN-PROGRESS.txt."])
        self.assertTrue((kept / "IN-PROGRESS.txt").is_file())
        self.assertTrue(check.measured)
        self.assertEqual(check.result(), "NOT UNCHANGED: 1 finding(s)")

    def test_what_cant_be_checked_stops_it_and_says_why(self):
        def changed(name: str, change):
            """Runs `change` on a file of the checkout's text, and gives what puts it back."""
            path = self.repo / name
            text = path.read_text()
            path.write_text(change(text))
            return lambda: path.write_text(text)

        baseline = lambda change: changed("data/baseline.json", lambda text: json.dumps(change(json.loads(text))))

        def with_presses(data: dict) -> dict:
            data["runs"][self.REPLAY]["press"] = "start@300"
            return data

        def with_a_long_name(data: dict) -> dict:
            data["runs"]["no input"] = data["runs"].pop("no_input")
            return data

        empty = self.folder / "empty"
        empty.mkdir()
        for why, args, change in (
                ("isn't a folder: give the shared folder's captures/", None, None),
                (f"--before {empty} holds no gate capture (no *.hash file)", ["--before", str(empty)], None),
                ("--jobs 0: at least one thing runs at a time", ["--jobs", "0"], None),
                (f"--disc {empty / 'none'}: not a folder", ["--disc", str(empty / "none")], None),
                ("data/dream-recomp.pin must hold a full 40-digit hash, not '6154c9a'", [],
                 lambda: changed("data/dream-recomp.pin", lambda text: "6154c9a\n")),
                (f"{self.REPLAY} plays a recording back, which the gate does on a new memory card and with no presses", [],
                 lambda: baseline(with_presses)),
                ("the run 'no input' names its files", [], lambda: baseline(with_a_long_name)),
                ("data/baseline.json isn't a baseline", [], lambda: changed("data/baseline.json", lambda text: "{}")),
                ("scripts/30_compare_runs.py and this script disagree on what describes a baseline run: note", [],
                 lambda: changed("scripts/30_compare_runs.py", lambda text: text.replace('"recorded_on"}', '"recorded_on", "note"}'))),
                ("games/jgr/jgr.toml doesn't name a disc image and a boot file", [],
                 lambda: changed("games/jgr/jgr.toml", lambda text: text.replace('image = "disc.gdi"', ""))),
        ):
            with self.subTest(why):
                restore = change() if change else None
                if args is None:  # CAPTURES itself
                    result = subprocess.run([sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(empty / "none"),
                                             "--disc", str(self.disc)], capture_output=True, text=True, env=self.env)
                else:
                    result = self.check(*args)
                if restore:
                    restore()
                self.assert_nothing_ran(result, why)
        # No disc folder given at all.
        result = subprocess.run([sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(self.captures)],
                                capture_output=True, text=True, env=self.env)
        self.assert_nothing_ran(result, "no disc folder: give --disc FOLDER or set JGR_DISC_DIR")
        # A capture folder inside the checkout would itself change the working tree the manifest records.
        (self.repo / "docs/captures").mkdir()
        result = subprocess.run([sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(self.repo / "docs/captures"),
                                 "--disc", str(self.disc)], capture_output=True, text=True, env=self.env)
        self.assert_nothing_ran(result, f"{self.repo / 'docs/captures'} is inside this checkout")
        self.assertEqual(list((self.repo / "docs/captures").iterdir()), [])
        # A working tree git can't read: what was built from couldn't be recorded.
        index = (self.repo / ".git/index").read_bytes()
        (self.repo / ".git/index").write_bytes(b"not an index")
        self.assert_nothing_ran(self.check(), "git can't say what this checkout's working tree holds (git status failed)")
        (self.repo / ".git/index").write_bytes(index)
        # Another check holds this checkout's build: its lock is a file there.
        (self.repo / "build").mkdir()
        with open(self.repo / "build/pin-check.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assert_nothing_ran(self.check(), "another pin check, or a run that one left behind, is using this checkout's build")
        # A copy of the scripts that is no checkout has no commit to name the folder by.
        shutil.rmtree(self.repo / ".git")
        self.assert_nothing_ran(self.check(), "isn't a git checkout with a commit")

    def test_ended_from_outside_it_stops_what_it_started_and_says_so_in_the_folder(self):
        self.behave(no_input=[{"sleep": 300}], attract=[{"sleep": 300}])

        def gone(pid: int) -> bool:
            try:
                return pathlib.Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z"
            except OSError:
                return True

        def free(lock) -> bool:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            return True

        def end_what_is_left():
            """Only when this test fails is anything left: the stand-in programs it started, by their own path."""
            for call in self.calls():
                with contextlib.suppress(OSError):
                    if str(self.repo).encode() in pathlib.Path(f"/proc/{call['pid']}/cmdline").read_bytes():
                        os.kill(call["pid"], signal.SIGKILL)

        self.addCleanup(end_what_is_left)
        # However it is ended: by a harness (SIGTERM), by a shell that closed (SIGHUP), or by hand (SIGINT).
        for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            with self.subTest(number.name):
                made = len(self.calls())
                check = subprocess.Popen([sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(self.captures), "--disc",
                                          str(self.disc), "--jobs", "2", "--label", number.name],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                self.addCleanup(check.kill)
                waited = 0.0
                while len(self.calls()) < made + 2:  # both are running: a run, and the gate's first scenario
                    self.assertIsNone(check.poll(), "it ended before it was stopped")
                    self.assertLess(waited, 60, "the stand-in program was never started")
                    time.sleep(0.05)
                    waited += 0.05
                check.send_signal(number)
                out, err = check.communicate(timeout=60)
                self.assertEqual(check.returncode, 128 + number, out + err)
                self.assertIn(f"31_pin_check.py: ended from outside ({number.name}): stopping what it started", err)
                for call in self.calls():  # no program is left running, the one the gate started included
                    self.eventually(lambda: gone(call["pid"]), f"still running: {call}")
                dest = self.captures / f"{self.name}-{number.name}"
                self.assertEqual(self.files(dest), ["IN-PROGRESS.txt"])
                marker = (dest / "IN-PROGRESS.txt").read_text()
                self.assertIn(f"for commit {self.commit[:7]} at pin {self.pin[:7]}", marker)
                self.assertRegex(marker, r"It was cut short at \d\d:\d\d UTC\.\n\Z")
                self.assertEqual(list((self.folder / "tmp").iterdir()), [])
                with open(self.repo / "build/pin-check.lock", "a") as lock:  # and the build is free again
                    self.eventually(lambda: free(lock), "the lock is still held")

    def test_an_error_of_its_own_is_never_taken_for_a_result(self):
        # Made up: the compare script's reading of a report fails in a way nothing here expects.
        compare = self.repo / "scripts/30_compare_runs.py"
        compare.write_text(compare.read_text() + "\n\ndef read_report(text):\n    raise RuntimeError('made up')\n")
        result = self.check("--jobs", "2")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("RuntimeError: made up", result.stderr)
        self.assertEqual(result.stderr.splitlines()[-1],
                         "31_pin_check.py: stopped by an error of its own, above. Nothing it printed is a result.")
        self.assertNotIn("UNCHANGED", result.stdout)
        self.assertNotIn("RUNS MATCH", result.stdout)
        dest = self.captures / self.name
        self.assertEqual(self.files(dest), ["IN-PROGRESS.txt"])
        self.assertRegex((dest / "IN-PROGRESS.txt").read_text(), r"It was cut short at \d\d:\d\d UTC\.\n\Z")
        self.assertEqual(list((self.folder / "tmp").iterdir()), [])  # the cards are gone, and nothing whole was left to keep

    def test_a_command_is_stopped_at_its_time_limit_with_what_it_started(self):
        pin_check = load("31_pin_check")
        beat = self.folder / "beat"
        # A command that starts another, which doesn't end when asked: both write, and neither ends on its own.
        command = ["sh", "-c", f'(trap "" TERM; while :; do date +%N >> "{beat}"; sleep 0.02; done) & '
                               f'while :; do date +%N >> "{beat}"; sleep 0.02; done']
        step = pin_check.Step("a run", command, self.folder / "log.txt", 0.5)
        began = time.monotonic()
        with contextlib.redirect_stdout(io.StringIO()) as said:
            step.run(())
        self.assertLess(time.monotonic() - began, pin_check.GRACE_SECONDS)
        self.assertIsNone(step.status)
        self.assertEqual(step.how(), "stopped, because it hadn't ended after 0 s")
        self.assertIn("a run ended: stopped, because it hadn't ended after 0 s", said.getvalue())
        time.sleep(0.3)  # a write that was under way when its process was killed has landed
        size = beat.stat().st_size
        self.assertTrue(size)
        time.sleep(0.3)
        self.assertEqual(beat.stat().st_size, size, "something it started is still running")
        # A command that ends in time gives its exit status, and what it printed is in its log.
        step = pin_check.Step("a run", ["sh", "-c", "echo printed; exit 3"], self.folder / "log.txt", 30)
        with contextlib.redirect_stdout(io.StringIO()):
            step.run(())
        self.assertEqual((step.status, step.how(), step.printed()), (3, "exit 3", ["printed"]))
        # Each thing that runs the game or reaches the network has its limit: the build 90 minutes,
        # and a run or the gate's capture 6 host seconds for each guest second, the gate's own two
        # scenarios of 40 s counted with its recording.
        plan = pin_check.Plan("c" * 40, "d" * 40, "ccccccc-ddddddd", self.captures / "none", self.disc, self.gdi, self.boot, None, 1, 1, self.RUNS, [])
        check = pin_check.Check(plan, self.folder / "out", self.folder / "cards", ())
        self.assertEqual([step.timeout for step in (check.build_step(), check.gate_step(), check.run_step("no_input", 1),
                                                    check.run_step(self.REPLAY, 2))], [5400, (80 + 1325) * 6, 3600, 7950])

    def test_a_check_that_is_killed_leaves_what_it_started_holding_the_build(self):
        """Killed, it can stop nothing. What it started goes on in the build folder, so the lock goes
        on with it, and no second check builds over a run that is still going."""
        self.behave(no_input=[{"sleep": 300}], attract=[{"sleep": 300}])
        check = subprocess.Popen([sys.executable, str(self.repo / "scripts/31_pin_check.py"), str(self.captures), "--disc",
                                  str(self.disc), "--jobs", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env)
        self.addCleanup(check.kill)
        waited = 0.0
        while not (self.calls("no_input") and self.calls("attract")):
            self.assertIsNone(check.poll(), "it ended before it was killed")
            self.assertLess(waited, 60, "the stand-in program was never started")
            time.sleep(0.05)
            waited += 0.05
        left = [call["pid"] for call in self.calls()]

        def end_what_was_left():
            """The programs, then the gate that started one of them: all gone once the lock is free."""
            for pid in left:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
            with open(self.repo / "build/pin-check.lock", "a") as lock:
                for _ in range(200):
                    with contextlib.suppress(BlockingIOError):
                        return fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    time.sleep(0.05)

        self.addCleanup(end_what_was_left)
        check.kill()
        check.wait()
        result = self.check("--label", "second")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("another pin check, or a run that one left behind, is using this checkout's build (build/pin-check.lock is held)",
                      result.stderr)
        self.assertEqual(len(self.calls()), len(left))


# The project's licence (README.md, "Licence"), named at the top of every file that holds code or
# configuration, so it goes with a file copied out of the repository.
LICENCE_ID = "GPL-2.0-only"
SPDX_LINE = f"SPDX-License-Identifier: {LICENCE_ID}"
SPDX_SUFFIXES = {".sh", ".py", ".bat", ".cmake", ".toml", ".yml", ".yaml"}
SPDX_NAMES = {"CMakeLists.txt", ".gitignore", ".gitattributes"}
SPDX_HEAD_LINES = 3  # after a shebang or a batch file's `@echo off`
# The FSF's text of the GPL, version 2, as gnu.org/licenses/old-licenses/gpl-2.0.txt has it. The
# licence lets it be copied only verbatim, and reflowed it once lost its last paragraph.
GPL2_SHA256 = "8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643"


class Licence(unittest.TestCase):
    def test_the_licence_is_the_fsf_text(self):
        self.assertEqual(hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest(), GPL2_SHA256)

    def test_every_code_and_config_file_names_the_licence(self):
        checked = 0
        # What git tracks, or every file in a copy without git, read from the working tree.
        for entry in audit.tracked_files(ROOT):
            path = entry.path
            if path.suffix.lower() not in SPDX_SUFFIXES and path.name not in SPDX_NAMES:
                continue
            if not path.is_file():  # deleted, and not yet staged
                continue
            head = path.read_text(encoding="utf-8").splitlines()[:SPDX_HEAD_LINES]
            with self.subTest(path.relative_to(ROOT).as_posix()):
                self.assertTrue(any(line.rstrip().endswith(SPDX_LINE) for line in head), head)
            checked += 1
        self.assertTrue(checked, "found no code or config file to check")


if __name__ == "__main__":
    unittest.main()
