# Commit map

On 5 November 2026, at the maintainer's request, the history of both repositories was made again with
Claude as author and committer, signed so GitHub shows every commit Verified. Each new commit has
exactly the same files as the old one, except that the dream-recomp pin and the hashes quoting it
point at the new dream-recomp commits. dream-recomp's own history before our four commits (phobos665's
and its contributors') is unchanged.

Old hashes still appear in names made before then: build folders such as
`2026-11-05-e06a4f9-pin-2013fb7`, capture folders, review packs and run logs. This maps them.

## Jet Set Recomp

| Old | New | Commit |
|---|---|---|
| `04fe8d0` | `7c8528b` | Add the GPL-2.0 licence and credits |
| `759a85f` | `d1882a0` | Add the project rules and docs |
| `805ce16` | `8995f18` | Add the game config and CMake layout |
| `b4346e0` | `ac513bd` | Add the build scripts, their tests and CI |
| `e06a4f9` | `e693252` | Keep the maintainer's name out of the repo |
| `46e0dd2` | `2e50e81` | Pin dream-recomp at 6c098df and record the baseline |
| `331787e` | `a71b7fc` | Mark the build scripts as run, and update the status |
| `3f6ac01` | `aaccbb3` | Keep a timestamped log for every run |
| `f2c263b` | `4b6e2ff` | Add a setup launcher to each package |
| `2aa22d3` | `4ef58a1` | Rename the project to Jet Set Recomp |
| `277669e` | `70bab3a` | Tighten the rules after the audit of 5 November |
| `5841c15` | `9900e62` | Make the launchers stop and say why when setup hasn't run |
| `026978d` | `3c36732` | Audit commit authors and messages, and add ShellCheck to CI |
| `0d4db23` | `d1da43b` | Bring the docs up to date after the audit |
| `e4cc456` | `3f0a416` | Keep gate captures between sandboxes in the shared folder |
| `f5d2caa` | `ff713fc` | Name the three principles code is built by |
| `e41ddb1` | `1723256` | Unblock agents where the rules left them stuck |
| `106c17a` | `5200eeb` | Name the harness defaults and fix wording that misleads agents |
| `4905e20` | `7ba69da` | Make the rules' defaults safe for parallel threads |
| `adc18b0` | `7794d6d` | Record sandbox speed in the baseline as a stand-in for performance |
| `f3158f2` | `272c0f0` | Add a git setup script for the project identity and signing |
| `23cab2c` | `4067047` | Fix what the sanity passes found in the second-pass rules |
| `b1d96b8` | `8441a3a` | Make play.sh's errors visible in Steam's Game Mode |
| `91ffffb` | `95b8434` | Fix what the fourth and fifth rules passes found |
| `3c8a00d` | `e130f46` | Give setup's disc scripts plain errors instead of tracebacks |
| `cd5f999` | `e1708ac` | Stop the build and package scripts early when their inputs are missing |
| `8b7a5fc` | `314bc65` | Record the maintainer's choices on coverage, the fallback and shadows |
| `0d6435a` | `3202350` | Author commits as Claude, signed by the sandbox, so GitHub verifies them |

## dream-recomp (our commits on `main`, after `51ca2766d2eb`)

| Old | New | Commit |
|---|---|---|
| `06a5564` | `9ba7d66` | Allow a build without the renderer |
| `1f689f0` | `daa598c` | Record the resume address in a resumed body's entry poll |
| `e25d2d9` | `21315e8` | Add DREAM_HOST_TRANSLATE for cross builds |
| `2013fb7` | `6c098df` | Add a Windows cross build for MinGW-w64 with clang |
