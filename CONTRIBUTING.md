# Contributing

Three rules first:

1. **Nothing from the disc, or made from it, ever goes in the repository:** the disc's files, any
   `.gdi` or `.chd`, `1ST_READ.BIN`, generated C++, built programs, memory cards, screenshots, or logs
   holding instruction text. Hashes, addresses, function names like `fn_0c014070` and counts are fine.
   `python3 scripts/audit_repo.py .` must report CLEAN.
2. **Generated code is never edited by hand.** Fix the translator, the runtime, the config or a named
   hook, then re-emit. Translator and runtime fixes go on
   [spriteice/dream-recomp](https://github.com/spriteice/dream-recomp), each with a unit test that
   fails without the fix.
3. **Everything here is GPL-2.0,** and docs stay respectful of dream-recomp and credit phobos665.

[docs/project-rules.md](docs/project-rules.md) has how a change is placed, written and checked.
[docs/build-and-test-reference.md](docs/build-and-test-reference.md) has building and testing.
Only Windows and Linux on x86-64 are considered.

To check the repository's own scripts, with no disc:

```sh
python3 scripts/audit_repo.py . --commits HEAD
python3 -m unittest discover -s tests
shellcheck scripts/*.sh packaging/*.sh
```
