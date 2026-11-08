# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the repository's own scripts. They use made-up data and need no disc.

    python3 -m unittest discover -s tests
"""
import hashlib
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_gdi = load("02_make_gdi")
audit = load("audit_repo")

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
        for hook in ("pre-commit", "commit-msg"):
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

    def test_it_installs_no_hooks_where_the_audit_isnt(self):
        """A dream-recomp clone has its own checks and no audit_repo.py, so it gets no hooks."""
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / ".git/hooks/pre-commit").exists())
        self.assertNotIn("runs at commit time", result.stdout)


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
