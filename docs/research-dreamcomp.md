> Research from 4 November 2026, before the test boot, written when the port was still part of another project. Kept for the alternatives it compares.

# dreamcomp, and a Dreamcast-only Jet Set Radio port

Research only, 2026-11-04. No repo changes. Everything below comes from the projects' public
README pages and GitHub search metadata (stars, created and pushed dates) as of today. Nothing
was built or run. Where a page didn't say something, this file says so instead of guessing.

## 1. What dreamcomp is

**dreamcomp exists.** It is `github.com/danielgomesvieira2000/dreamcomp`: "Framework for native
PC ports of Dreamcast games (SH-4 static recompilation, built on dream-recomp). No game data
included."

| | |
|---|---|
| Author | GitHub user `danielgomesvieira2000` (no other name given). Not sp00nznet. |
| License | GPL-2.0 (ports built on it are GPL-2.0 too) |
| Engine | **dream-recomp** by `phobos665`, vendored as a git subtree in `engine/`, pinned, with every local change logged in `docs/engine-changes.md` for upstreaming |
| Age, activity | Created 2026-10-08 15:36 UTC, last push 2026-10-08 15:48 UTC: published once, no upstream pushes in the 27 days since. 3 stars. Forks are where the work goes on: `cherryduck/dreamcomp` (pushed 2026-10-16, Ecco), `fenrircl/dreamcomp` (2026-10-23, Berserk), `WildGer/dreamcomp` (no changes) |
| How it works | SH-4 code is recompiled ahead of time to C++. Hardware runs as native code around it. Each game is its own repo under `ports/<slug>/` holding only config, hooks and docs. `cmake/DreamcompPort.cmake` gives `dreamcomp_add_port()`. `tools/dc.py` does setup, build, run, screenshots and reports; `tools/audit.py` scans for game data, tracks engine changes and lints docs |
| Hardware | PowerVR2 graphics, AICA sound with its ARM7, GD-ROM, Maple (controllers, VMU saves, rumble). BIOS calls are replaced by native code, so no BIOS image is needed (this part is from dream-recomp's README) |
| Hosts | Windows x64 built and tested (clang-cl, Vulkan, Intel Iris Xe). Linux compiles with g++ 15, "verified headless" only. macOS is the engine's own dev platform. Android planned |
| Renderer | Vulkan only. No OpenGL backend is mentioned |
| AI | Built with Claude Code as a stated part of the method: `CLAUDE.md`, `.claude/skills`, audits, `Co-Authored-By` trailers. The same way we work |

### Games that use it

| Game (disc) | Repo | Reported state |
|---|---|---|
| Soulcalibur (USA, T1401N) | `danielgomesvieira2000/soulcalibur-recomp`, 20 commits | Intro, menus, arcade fights, VMU saves, 4 players, rumble. 4x real time on Iris Xe at 2x res. 8 min scripted play per seed with no faults. Windows only. Widescreen crashes in fights (the one listed bug) |
| Ecco: Defender of the Future (EU, MK-5103350) | `cherryduck/ecco-the-dolphin-defender-of-the-future-recomp`, 7 commits, plus a `linux-ecco` branch of the dreamcomp fork | Whole game played through on Linux x64 (Vulkan, Wayland). 17,574 recompiled functions, 0 untranslated calls in menus and gameplay. Windows and macOS untested. ~1% of the screen shows translucency order errors. Busy-waits on vblank because dreamcomp's idle-skip hook "doesn't apply to this game's library" |
| Ecco on PS5 | `cherryduck/PS5_EccoDefender` | Exists, not examined |
| Berserk (JP v1.001) | `fenrircl/berserk-dc-recomp` | "Early research": skips logos, reaches the main menu, doesn't start a new game. Windows x64 tested |
| Rez (via Deadcast) | `tyrannotorus/emulator-dreamcast-deadcast` | A Flycast fork for the TrimUI handheld that launches dreamcomp-built modules. Not relevant to PC |

## 2. The engine underneath: dream-recomp

`github.com/phobos665/dream-recomp`, GPL-2.0, 73 commits, created 2026-09-13, last push
2026-10-29, 10 stars, at least 4 other forks pushed in the last 3 weeks.

- Takes a `.chd` or `.gdi` disc image and makes a native executable; the output "contains no SH-4
  instructions". Modelled on N64Recomp and XenonRecomp. Parts of Flycast (GPL-2.0) are ported in
  on purpose (that is why it's GPL), and **Flycast's interpreter is the test oracle**: a
  differential harness compares translated code against it instruction by instruction, and every
  emitter change is expected to come with a case. Also `--write-hash` (per-frame hash of memory
  writes, to compare runs) and F11 capture for offline replay. This lines up with our own rule:
  lifter fixes come with a difftest case.
- Memory: 16 MB RAM, 8 MB VRAM, store queues. SH-4: delay slots, FPU modes, interrupts. MMU isn't
  mentioned.
- **Katana titles only.** Windows CE titles are refused (the README puts them at about a tenth of
  the library).
- Its own honesty note: the project is "partial". Function discovery finds about 79 to 90% of a
  typical binary, and **no title builds without the interpreter fallback yet**. Per-game config
  (a TOML: identity, layout, relocations, extra function seeds) fills the gaps, and
  `--suggest-config` proposes entries.
- Titles in its own README: Crazy Taxi plays (music, gameplay, saves); Tech Romancer draws its
  options screen; Metropolis Street Racer boots slowly, mostly interpreted; Charge 'N Blast boots
  and renders. Elsewhere: Rayman 2 (`phobos665/Raymanian-2-recomp`) ran 898 frames with no fault
  and no untranslated targets, its config needed only 4 relocations and no extra function seeds;
  deSPIRIA has a kit (`goodshepherd23/deSPIRIA-DreamRecomp`).
- Hosts: macOS, Windows, Linux. CMake 3.24+, C++20 (clang 16+ or MSVC 2022), Python 3.9+. Vulkan,
  SDL3 and glslc are optional; without them it runs headless.

## 3. Nearby alternatives

| Project | Author, license | State | Notes |
|---|---|---|---|
| **dcrecomp** | sp00nznet (pcrecomp's author). README says MIT and "no GPL emulator code"; GitHub's license detection says GPL-2.0, so check before relying on either | Its Crazy Taxi (`sp00nznet/crazytaxi`) links 12,750 functions and takes interrupts but "does not draw a frame yet". Also Naomi (Mushiking runs with SDL2 + GL) | SH-4 to C. AICA is a stub. OpenGL 3.3 renderer, "basic". Planned accurate backend would link Flycast in a separate GPL repo. Created 2026-03, last push 2026-10-20. Less far along than dream-recomp |
| **KatanaRecomp** | Not found publicly | Powers `sonicfreak1337/SARecomp`: Sonic Adventure "fully playable", all 7 stories, Windows, Linux and Steam Deck, D3D11 or Vulkan. v0.50.0-beta.1 | The closest to what we'd want (a Sega first-party Katana game on SteamOS), but the recompiler itself isn't published and development is "halted for personal reasons" |
| One-game toolchains | various | Several are playable | `enrique363/voldorium` (Soulcalibur, own SH-4 to C, OpenGL, rollback netcode, non-commercial license). `irnutsmurt/Street-Alpha-3-Dreamcast-Recomp` (own, Vulkan, Windows + Linux, GPL-3). `ZoomiesZaggy/Space-Channel-5` (own AOT plus Flycast devices, OpenGL 3.3, GPL-2, preview). `DCRecomp/BlueStingerRecomp` (own, Vulkan + software, Windows only, MIT, "~81%"). Initial D Arcade Stage 3 (NAOMI 2, own, Vulkan, no license stated) |
| `Duw0ng/DreamcastRecompiled` | MIT | Experimental | Not examined further |

## 4. How it could fit a Dreamcast-only Jet Set Radio port

**What lines up**

- Jet Set Radio isn't on retroreversing.com's list of Windows CE Dreamcast titles, so it's very
  likely a Katana title, which is the one kind dream-recomp accepts. To confirm on a disc: a WinCE
  disc has `0WINCEOS.BIN` in its root and a PE `.EXE`; a Katana disc boots `1ST_READ.BIN`.
- The hardware it needs is all there: PowerVR2, AICA + ARM7, GD-ROM, Maple, VMU saves, no BIOS.
  Players would bring only their own Dreamcast disc.
- The method matches ours: per-game repo holding config and hooks only, generated code never
  committed, a difftest-style oracle for lifter fixes, audit tooling for game data, and Claude Code
  as the stated workflow.
- Disc choice: TCRF says the 2012 HD version was made by Blit Software from the European release
  (De La Jet Set Radio content). The Dreamcast Junkyard's comparison: the US and EU releases add
  the extra Grind City stages, EU adds the most music, De La (JP) is EU content with Japanese
  voices. dreamcomp ports pin one release by its boot-file hash, so we'd pick one.

**What doesn't line up with our rules**

1. **Renderers.** Our rule is Vulkan plus OpenGL 3.3 core on both OSes. dreamcomp and dream-recomp
   are Vulkan only, so a GL backend would be ours to write (Flycast's GL renderer is GPL-2, so it
   could be ported in).
2. **Linux and SteamOS.** dreamcomp is tested on Windows; Linux is "headless verified". Only the
   Ecco fork has shown full play on Linux. Nothing built on it has been tried on SteamOS.
3. **Vendoring.** dreamcomp vendors its engine as a subtree. Our pcrecomp rule is "pinned and
   fetched, never vendored". For a Dreamcast project we'd want the same: pin dream-recomp and fetch
   it, and keep dreamcomp only as a template, or fork it and change that.
4. **Upstream health.** dreamcomp upstream hasn't moved since 2026-10-08. dream-recomp is the
   active one, so it's the thing to depend on.
5. **Interpreter fallback.** dream-recomp says no title builds without it yet. Ports report 0
   untranslated calls once tuned, but at the start JSR would likely lean on it.
6. **License.** Everything here is GPL-2.0. A JSR Dreamcast port would be a new GPL-2.0 repo,
   separate from JSR-PC (which has no LICENSE file yet).

**Unknowns only a test can answer**

How far discovery gets on JSR's `1ST_READ.BIN`, and whether the PowerVR2 renderer gets JSR's
look right (its cel shading and outlines, translucency sorting, and spray-painted graffiti).
None of these tools say anything about JSR, and nobody has published a JSR Dreamcast recomp
(GitHub search for "jet set radio dreamcast" and "jet set radio recomp" finds only JSRF and
unrelated projects).

## 5. Recommendation

dreamcomp is real and is the best-documented route, but use its engine, **dream-recomp**, as the
dependency and dreamcomp as the template, since dreamcomp upstream has gone quiet. Make it a
separate project ("JSR-DC"), not a change of direction for JSR-PC: JSR-PC is further along (M1
done, 18,102 functions lifted) and already matches our renderer and platform rules.

The cheapest next step is a feasibility boot, done in a cloud sandbox or on the PC with your own
Jet Set Radio Dreamcast disc dump (`.gdi` or `.chd`), kept there under section 3. It would report
in numbers: functions discovered, untranslated calls, interpreter share, frames reached before the
first fault, and whether the title screen draws. Its result decides whether a full JSR-DC project
is worth opening. That would need its own rules docs, including how the GL-renderer and SteamOS
gaps get closed.

## Sources

- dreamcomp: https://github.com/danielgomesvieira2000/dreamcomp
- dream-recomp: https://github.com/phobos665/dream-recomp
- Soulcalibur on dreamcomp: https://github.com/danielgomesvieira2000/soulcalibur-recomp
- Ecco on dreamcomp: https://github.com/cherryduck/ecco-the-dolphin-defender-of-the-future-recomp
- Berserk on dreamcomp: https://raw.githubusercontent.com/fenrircl/berserk-dc-recomp/HEAD/README.md
- Rayman 2 on dream-recomp: https://raw.githubusercontent.com/phobos665/Raymanian-2-recomp/HEAD/README.md
- Deadcast: https://github.com/tyrannotorus/emulator-dreamcast-deadcast
- dcrecomp: https://github.com/sp00nznet/dcrecomp
- Crazy Taxi on dcrecomp: https://raw.githubusercontent.com/sp00nznet/crazytaxi/HEAD/README.md
- SARecomp (KatanaRecomp): https://github.com/sonicfreak1337/SARecomp
- voldorium: https://github.com/enrique363/voldorium
- Street Fighter Alpha 3: https://raw.githubusercontent.com/irnutsmurt/street-alpha-3-dreamcast-recomp/HEAD/README.md
- Space Channel 5: https://github.com/ZoomiesZaggy/Space-Channel-5
- Blue Stinger: https://github.com/DCRecomp/BlueStingerRecomp
- Initial D AS3: https://github.com/distilledorion-sketch/Initial-D-Arcade-Stage-3-Native-SH-4-Recompilation-WIP-
- WinCE title list and how to spot one: https://www.retroreversing.com/dreamcast-windows-ce
- JSR 2012 (Blit Software, EU base): https://tcrf.net/Jet_Set_Radio_(2012)
- Regional differences: https://www.thedreamcastjunkyard.co.uk/2012/03/which-version-of-jet-set-radio-is-best.html
