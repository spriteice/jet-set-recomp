"""Tests for the repository's own scripts. They use made-up data and need no disc.

    python3 -m unittest discover -s tests
"""
import importlib.util
import pathlib
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


if __name__ == "__main__":
    unittest.main()
