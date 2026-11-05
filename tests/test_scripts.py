"""Tests for the repository's own scripts. They use made-up data and need no disc.

    python3 -m unittest discover -s tests
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess
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

    def test_a_session_link_is_found(self):
        link = ("https://" + "claude" + ".ai/code/abc").encode()
        self.assertIn("a Claude session link", self.findings("notes.md", link))

    def test_generated_code_is_found(self):
        code = b"static void fn_0c014070" + b"__resume(Ctx& c, Memory& m, std::uint32_t resume_pc) {"
        self.assertIn("generated C++", self.findings("notes.cpp", code))

    def test_instruction_text_is_found(self):
        self.assertIn("instruction text", self.findings("trace.log", b"0c014070: 4f22 sts.l pr,@-r15\n"))

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
    (folder / "prefix/lib/libSDL3.so.0").write_text("")
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
        for name in ("jgr_boot", "jgr.toml", "play.sh", "setup.sh", "README.txt",
                     "tools/02_make_gdi.py", "tools/03_get_boot_file.py", "tools/inputs.sha256",
                     "tools/dcdisc/__init__.py", "licences/LICENSE-jet-set-recomp.txt",
                     "licences/LICENSE-dream-recomp.txt"):
            self.assertTrue((self.out / name).exists(), name)

    def test_the_package_holds_nothing_from_the_disc(self):
        for name in ("disc.gdi", "boot"):
            self.assertFalse((self.out / name).exists(), name)

    def play(self):
        return subprocess.run(["sh", str(self.out / "play.sh")], capture_output=True, text=True)

    def test_play_stops_and_says_why_before_setup(self):
        result = self.play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run setup first", result.stderr)
        self.assertFalse((self.out / "ran.txt").exists())

    def test_play_runs_with_a_timestamped_log_after_setup(self):
        (self.out / "disc.gdi").write_text("")
        (self.out / "boot").mkdir()
        (self.out / "boot/1ST_READ.BIN").write_text("")
        self.assertEqual(self.play().returncode, 0)
        args = (self.out / "ran.txt").read_text()
        self.assertRegex(args, r"--report logs/run-\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.txt")
        self.assertTrue((self.out / "logs").is_dir())


if __name__ == "__main__":
    unittest.main()
