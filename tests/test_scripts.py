"""Tests for the repository's own scripts. They use made-up data and need no disc.

    python3 -m unittest discover -s tests
"""
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
        return subprocess.run(["sh", str(self.out / "play.sh")], capture_output=True, text=True,
                              env=dict(os.environ, JGR_NO_DIALOG="1"))

    def test_play_stops_and_says_why_before_setup(self):
        result = self.play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run setup first", result.stderr)
        self.assertIn("Run setup first", (self.out / "logs/launcher.txt").read_text())
        self.assertFalse((self.out / "ran.txt").exists())

    def test_play_runs_with_a_timestamped_log_after_setup(self):
        (self.out / "disc.gdi").write_text("")
        (self.out / "boot").mkdir()
        (self.out / "boot/1ST_READ.BIN").write_text("")
        self.assertEqual(self.play().returncode, 0)
        args = (self.out / "ran.txt").read_text()
        self.assertRegex(args, r"--report logs/run-\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d\.txt")
        self.assertTrue((self.out / "logs").is_dir())


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


class GitSetup(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.repo = self.folder / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.global_config = self.folder / "gitconfig"
        self.global_config.write_text("")

    def setup(self):
        env = dict(os.environ, HOME=str(self.folder), GIT_CONFIG_GLOBAL=str(self.global_config))
        return subprocess.run(["bash", str(ROOT / "scripts/08_git_setup.sh"), str(self.repo)],
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


if __name__ == "__main__":
    unittest.main()
