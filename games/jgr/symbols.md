# Named addresses in Jet Grind Radio (USA)

The game's functions and data that the two studies of 14 November 2026 named, for the hooks and phase 6
([docs/plan.md](../../docs/plan.md)). Every address is the USA release's: Jet Grind Radio, MK-51058 V1.005,
whose boot file `data/inputs.sha256` checks. The European and Japanese discs have their own addresses, and
none of these is known to hold there.

Only addresses, names and counts are here. The names are the studies', made from what each thing was seen
to do: guesses from behaviour, good enough to work with. Nothing reads this file yet.

Both studies ran a headless build of this repository (the camera study at `3dec93a`, the game study at
`5c89491`) with dream-recomp at the pin `6154c9a`, replaying recording 1
(`data/recordings/2026-11-08-tutorial-mission1-kogane.txt`), so a frame number is that recording's. The
"Study" column says which one named each address:

- **Camera:** the camera study, section 6 of the shared folder's `reviews/camera-study-2026-11-14.md`. A
  watch is the launcher's store watch, `DREAM_WATCH_WRITE=ADDR:LEN`, at the frames named.
- **Game:** phase 6's game study, section 10 of the shared folder's `phase6/game-study-2026-11-14.md`.
  Runs A to I are its whole-recording runs, listed in its section 11, and "the write log" is
  `--write-log` of one picture. Its read watches, and its knock-outs, which point one class's draw at
  `empty_function` for the ten frames before a capture so that what vanishes names the class, used
  switches added to a copy of dream-recomp that stayed in the study's sandbox.

One name differs from its study: the game study named both the circle tests and their data
`cull_circle_0` to `_2`, so the data is `cull_circle_record_0` to `_2` here. A cell that pointed at a
study's own section says which study now.

`genindex.py`, `tasks.py`, `peek.py`, `findval.py` and `find_matrices.py` are the studies' scratch scripts,
in the shared folder's `study-tools/`.

A function's address is where the translator starts it, so `0x0C01DC40` is `fn_0c01dc40` in the emitted
code, and each is a whole function that the translator emits. Data is named by the address the game uses,
in the cached `0x8C` segment of the same memory.

## Functions

### The camera

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C01DC40` | `camera_update` | The camera object's step: picks the mode's function, then makes the final camera | `genindex.py asm`, and a store watch on the object | Camera |
| `0x0C01E424` | `camera_follow` | The follow camera. 673 instructions, one caller | The same | Camera |
| `0x0C01F7E0` | `camera_snap_behind` | Puts the eye behind the player (L, and after a big graffiti) | Watch: mode 5 at each L press | Camera |
| `0x0C02043C` | `camera_reset` | Start values, when the object is made or the player asks (`player+0x9C`) | `genindex.py asm` | Camera |
| `0x0C01DABC` | `camera_start` | Makes the four line-test records and calls the reset | `genindex.py asm` | Camera |
| `0x0C01EB80` | `camera_big_graffiti` | The big graffiti's view | Watch: mode 4 from 19,164 | Camera |
| `0x0C01F04C` | `camera_pose` | The start and "cleared" poses | Watch: modes 6 and 1 | Camera |
| `0x0C01F2A0` | `camera_asked_view` | Runs when `player+0x864` is set. Not seen running | `genindex.py asm` only | Camera |
| `0x0C01F544`, `0x0C01F8E4`, `0x0C01FB3C`, `0x0C01FD6C`, `0x0C01FF8C` | `camera_ideal_0` to `_4` | The ideal eye and target, for the player's states 0, 3, 4, 5 and 6 | The state table at `0x0C01E754` | Camera |
| `0x0C01E29C` | `camera_ask_walls` | Hands in the two wall lines | `genindex.py asm` | Camera |
| `0x0C0201F0` | `camera_close_wall` | Builds the override camera when a wall is close to the player | `genindex.py asm` only | Camera |
| `0x0C01E238`, `0x0C01E080` | `camera_draw`, `camera_keep` | The draw side: blend two kept cameras, give the result to `0x0C020580` | `genindex.py asm` | Camera |
| `0x0C0B648C` | `line_test_ask` | Hands one line to the collision code: fills the query's record, clears its result and queues it (the camera study's section 4) | `genindex.py asm` | Camera |
| `0x0C0B646C` | `line_test_new` | Makes a line-test record. 63 callers | `genindex.py info` | Camera |
| `0x0C0B5E7C` | `line_test_answer` | Answers the queue | Watch: it stores the camera's results | Camera |

### The player, its input and the pad

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C0198F8` | `player_update` | The player object's step | Watch on the player object | Camera |
| `0x0C01B754` | `player_ask_recentre` | Sets `player+0x84` when L was pressed. 17 instructions, one caller | Watch, then `genindex.py asm` | Camera |
| `0x0C06C048`, `0x0C01A8A8`, `0x0C042CBC` | `player_steer_ground`, `_b`, `_c` | The three functions that read the camera's angle for the controls | `genindex.py lit 0x850` | Camera |
| `0x0C08E7A8` | `small_tag_view_start` | Sets the small tag's view fields in the player | Watch at 15,138 | Camera |
| `0x0C0278C0`, `0x0C027C74` | `input_update`, `input_from_pad` | The input object's step, and the pad read | `genindex.py asm` | Camera |
| `0x0C02775C`, `0x0C027788`, `0x0C0277A0` | `input_pressed`, `input_stick_angle`, `input_stick_amount` | How the player asks the input object | `genindex.py asm` | Camera |
| `0x0C0B2828` | `pad_copy` | The game's copy of SEGA's pad record, once a step | `genindex.py callers fn_0c28951c` | Camera |

### Objects

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C0B2D2C`, `0x0C0B3858` | `task_run`, `task_find` | The task runner, and "find the object with this number" | Watch, `genindex.py info` | Camera |
| `0x0C0B3524` | `task_make` | Makes an object: `+12` made, `+16` step, `+20` draw | `tasks.py` on 16 images | Game |

### The screen, and the library's lists

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C020580` | `view_set` | Calls the library's set-up and copies the camera to `0x8C2E9930` | A store watch on `0x8C32E1F0` | Camera |
| `0x0C27A7C8` | `lib_camera_setup` | Sets the screen block from a camera: distance from the view angle, near, far, matrix | Run B: a write watch on `0x8C32E0F8` to `0x8C32E157` | Game |
| `0x0C27A7B0` | `lib_set_scale` | Sets the horizontal and vertical scale. Its one game call (`0x0C10111A`) never ran | Run B, and `genindex.py callers` | Game |
| `0x0C27AB28` | `lib_set_perspective` | Sets the distance from a view angle | Run B | Game |
| `0x0C27AB50` | `lib_set_projection` | Sets the distance and the centre directly. Places 3D things in the HUD and the menus | Run B | Game |
| `0x0C27BD2A` | `lib_screen_init` | Writes the scale words once, at frame 23 | Run B | Game |
| `0x0C27D07A` | `lib_screen_save` | Copies the width to `0x8C32E120` for six game callers | Run C: a read watch on the block | Game |
| `0x0C27CB16` | `lib_background_build` | Builds the background plane from the width and the height | Run C, and `genindex.py asm` | Game |
| `0x0C225FE0` | `lib_lists_queue` | Queues the picture's four channel-2 DMA entries at `0x8C302618` | A write log of one picture (45,300) | Game |
| `0x0C21FB60` | `lib_lists_start` | Starts them, from the DMA-end handler `0x0C2239F0` | The same | Game |
| `0x0C2260E0` | `lib_wait_picture` | Waits for the end of the picture | Run D: a CPU sample every 200,000 cycles | Game |

### 2D, the HUD and full-screen effects

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C2728AC` | `lib_draw_2d` | Textured 2D: a vertex array in memory (`r4`, six words a vertex), count `r5`, texture `r6`, flag `r7`. The HUD | The write log: it wrote the HUD's stores | Game |
| `0x0C2727FC` | `lib_draw_2d_flat` | Untextured 2D quads (bars, fades' boxes) | The same, and `genindex.py callers` | Game |
| `0x0C272518` | `lib_draw_2d_b` | A third 2D shape, 12 callers | `genindex.py callers` | Game |
| `0x0C0B0C58` | `hud_build` | Builds the HUD's vertex arrays on the stack, from `0x0C0B0AA4` | The write log at 45,300 | Game |
| `0x0C026F68` | `letterbox_draw` | The letterbox bars' draw. Made by `0x0C026DC8` (`letterbox_make`) | `tasks.py` on images at 3,600, 8,400 and 49,800 | Game |
| `0x0C036024` | `hud_points_draw` | The HUD's points counter | Knock-out at 47,700 | Game |
| `0x0C0210B8` | `fade_draw` | The full-screen fade, level at `+0x74`. Made by `0x0C021048` | The write logs at 14,700, 16,500 and 29,100 | Game |

### Culling and draw ranges

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C0C287C` | `cull_build` | Builds the three wedges and places the three circles, from `view_now`, every draw pass | Run G: a read watch on `0x8C2E2CFC` to `0x8C2E2DBF` | Game |
| `0x0C0C32CC`, `0x0C0C3344`, `0x0C0C33BC` | `cull_wedge_0` to `_2` | The wedge tests. 35, 5 and 3 callers | Run G, `genindex.py callers` | Game |
| `0x0C0C3470`, `0x0C0C3498`, `0x0C0C34C0` | `cull_circle_0` to `_2` | The circle tests. 30, 29 and 5 callers | The same | Game |
| `0x0C0C3434`, `0x0C0C3448`, `0x0C0C345C` | `cull_circle_set_0` to `_2` | Set a circle's radius (stored squared) and forward offset | `genindex.py asm` | Game |
| `0x0C0C2284` | `cull_defaults` | Circle 0's default (500, 300), at each level start | Run G's writes | Game |
| `0x0C02F5A4`, `0x0C039AF0`, `0x0C03A72C` | `level_cull_shibuya`, `level_cull_kogane`, `area_cull_kogane` | The levels' circle and wedge values (the game study's section 7) | Run G's writes | Game |
| `0x0C0C9D50` | `cull_cone` | A sphere against the view's cone and a far depth. Returns the depth. 18 callers | `genindex.py asm`, and `--dump` of the cone words | Game |
| `0x0C0C9DD0` | `cull_cone_mesh` | The same for each mesh, inside `0x0C0C9E64` (`model_draw`, 33 callers) | `genindex.py asm` | Game |
| `0x0C0C9D08` | `cull_cone_set` | Sets the cone from the view angle times 1.2 | `genindex.py asm`, `--dump` at three spots | Game |
| `0x0C06DD7C` | `char_cull` | The characters' test: the cone, then near, middle and far (the game study's section 7) | `genindex.py asm` | Game |
| `0x0C089B78` | `crowd_ranges` | Sets the crowd's ranges each picture, scaled by the view angle | Run G, `genindex.py asm` | Game |

### What draws each class

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C0DB2B8`, `0x0C0DB6EC` | `can_draw_a`, `can_draw_b` | Spray cans | Knock-out at 51,640 | Game |
| `0x0C06B920` | `car_draw` | Cars. Made by `0x0C06B318` | Knock-outs at 26,400 and 45,300 | Game |
| `0x0C09146C`, `0x0C091F64` | `bus_draw_a`, `bus_draw_b` | Buses. Made by `0x0C091334` and `0x0C0915E4` | Knock-out at 50,100 | Game |
| `0x0C08A2C0`, `0x0C08A62C` | `crowd_draw_a`, `crowd_draw_b` | The crowd. Made by `0x0C089C00`. Tested by `0x0C08B608` (`crowd_cull`) | Knock-out at 8,400 | Game |
| `0x0C019CFC` | `player_draw` | The player | `tasks.py`, `genindex.py asm` | Game |
| `0x0C0778B4`, `0x0C0933AC` | `police_draw_a`, `police_draw_b` | Police on foot. Made by `0x0C076310` and `0x0C0929BC` | Knock-out at 55,800 | Game |
| `0x0C0DFA7C` | `rival_draw` | A rival skater. Made by `0x0C0DF5AC`. Tested by `char_cull` with 100, 250 and 400 | Knock-out at 47,700 | Game |
| `0x0C0CC7C8` | `cutscene_police_draw` | The police cutscene's cars and officers. No test. Made by `0x0C0CC29C` | Knock-out at 49,800 | Game |
| `0x0C0578C0`, `0x0C04DDF4`, `0x0C0E4AE8`, `0x0C0F0490` | `bike_draw`, `spot_arrow_draw`, `cone_prop_draw`, `pole_draw` | Bicycles, the graffiti spots' arrows, traffic cones, striped poles | Knock-outs at 27,240 and 45,300 | Game |

### Graffiti

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x0C03AEDC`, `0x0C03B0FC` | `tag_reach`, `graffiti_main` | Finds a tag in reach on an L press, and runs the spraying | Watch at 19,162 and 19,164 | Camera |
| `0x0C095380` | `graffiti_load` | Loads the player's three graffiti textures (the game study's section 8). 20 callers, 22 runs | `grep` of the emitted code for `0x8cf80000`, and run I | Game |
| `0x0C2799D4` | `lib_texture_load` | Copies a texture from memory into a slot of the library's table | `genindex.py asm` | Game |

## Data

### The camera and the view

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C2E9930` | `view_now` | The camera in use, 64 bytes: eye, direction, roll, view angle, near, far | `--dump`, then `findval.py` | Camera |
| `0x8C2FCE40` | `view_matrix` | The view's 4x4 matrix | `find_matrices.py` on two images | Camera |
| `0x8C2E7118` | `task_slot_camera` | A slot of the task system. It points to the camera object while a level has one, else 0 | A store watch to frame 78,800 | Camera |
| `0x8C10A760` | `camera_offsets` | The follow camera's table of offsets, to `0x8C10A7FF` | `genindex.py lit` | Camera |

### The pad

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C2E48CC`, `0x8C2E488C`, `0x8C2E486C` | `pad_buttons`, `pad_stick`, `pad_triggers` | The game's copy of the pad's buttons, first stick and triggers, made once a step by `pad_copy`. Four ports, 12, 16 and 8 bytes each (the camera study's section 5) | `genindex.py asm fn_0c0b2828` | Camera |
| `0x8C338EA4` | `sega_pad_a` | SEGA's pad record, port A, 52 bytes: buttons, triggers and the first stick. The second stick's fields (`+0x20`, `+0x22`) stay 0 (the camera study's section 5) | A store watch on it | Camera |
| `0x8C2E9D20` | `pad_raw_a` | The pad's raw answer, with a copy at `0x8C2EA120`: both sticks, the second's two bytes at `+0x0E` and `+0x0F` (the camera study's section 5) | The second-stick run | Camera |

### The screen, and the library's lists

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C32E0F8` | `lib_screen` | The library's screen block: the distance at `+0`, the width `+4`, the height `+8`, the matrix pointer `+0x14`, near `+0x2C`, far `+0x30`, horizontal and vertical scale `+0x34` and `+0x38` | Runs B and C | Game |
| `0x8C32DEE4` to `0x8C32DEF4` | `lib_list_pos` | The five lists' write positions (the game study's section 4) | The write log at 45,300 | Game |
| `0x8C302618` | `lib_list_dma` | The four DMA entries, 32 bytes each | The same | Game |

### Culling and draw ranges

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C2E2DB8`, `0x8C2E2D8C`, `0x8C2E2D60` | `cull_wedge_margin_0` to `_2` | Added to the view angle before halving. 0 at every spot read | Run G, `--dump` | Game |
| `0x8C2E2DB4`, `0x8C2E2D88`, `0x8C2E2D5C` | `cull_wedge_back_0` to `_2` | How far each wedge's apex sits behind the eye | The same | Game |
| `0x8C2E2DBC` | `cull_wedge_scale` | Scales the apex distances: 1, or 6 or 3 when `0x8C2E9998` is set | The same | Game |
| `0x8C2E2D24` to `0x8C2E2D30`, `0x8C2E2D10` to `0x8C2E2D1C`, `0x8C2E2CFC` to `0x8C2E2D08` | `cull_circle_record_0` to `_2` | Each circle's centre, forward offset and radius squared | The same | Game |
| `0x8C2FAD8C`, `0x8C2FAD88` | `cull_cone_tan`, `cull_cone_sec` | The cone's tangent and the inverse of its cosine | `--dump` at 45,300, 49,800 and 52,800 | Game |
| `0x8C0C9D3C` | `cull_cone_factor` | 1.2: the cone's half-angle over the view angle, read from memory each time | `genindex.py asm`, and the widescreen runs | Game |
| `0x8C06BA70` | `car_near` | 625, 3,600, 2,975: the cars' near fade, squared | `peek.py` on the 45,300 image | Game |
| `0x8C092030` | `bus_step` | 90,000: the buses' step at 300 | The same | Game |
| `0x8C2C5B64` to `0x8C2C5B74` | `crowd_range` | The crowd's ranges this picture (the game study's section 7) | `peek.py` on four images | Game |
| `0x8C1B9638` | `crowd_range_base` | Their values at 75° | `genindex.py asm fn_0c089b78` | Game |
| `0x8C1B7264`, `0x8C1BA110` | `police_range_a`, `police_range_b` | 100, 300, 600 | `peek.py` on the 50,100 and 52,800 images | Game |
| `0x8C1B4C68` | `char_fade` | The fade `char_cull` writes | `genindex.py asm` | Game |

### Full-screen effects

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C0270F0`, `0x8C0270F4` | `letterbox_left`, `letterbox_right` | -1 and 640, the bars' edges | `genindex.py asm fn_0c026f68` | Game |

### Objects

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8C01705C` | `empty_function` | The game's own empty function, 67 uses. The knock-outs point draws at it | `genindex.py lit` | Game |

### Graffiti

| Address | Name | What it is | The command that showed it | Study |
|---|---|---|---|---|
| `0x8CF80000`, `0x8CFA0000`, `0x8CFB0000` | `graffiti_xl`, `graffiti_l`, `graffiti_s` | The player's graffiti textures in memory | A byte compare of memory images and video memory | Game |
| `0x8C2C5BE0` to `0x8C2C5BE8` | `graffiti_sets` | The three sizes' texture sets | `genindex.py asm fn_0c095380` | Game |
| `0x8C2AD46C` | `lib_texture_table` | A pointer to the library's texture table, 12 bytes an entry, the video address at `+8` | `genindex.py asm fn_0c2799d4` | Game |

## The camera object

From the camera study. It is made new for each trial and level, so its address changes, and a
hook takes it from the function's own argument (the camera study's first answer).

| Offset | What it holds |
|---|---|
| `+0x18` | The player (every object's `+0x18` is its parent) |
| `+0x70` | Mode: 3 follow, 5 snapping behind, 4 big graffiti, 6 and 1 the poses, 7 asked for by the player's state 1 |
| `+0x74` | The follow camera's wall state |
| `+0x7C`, `+0x88` | The eye, and its ideal place |
| `+0x94`, `+0xA0` | The target, and its ideal place (the player, 14 up) |
| `+0xC0` | The view angle to use (`0x3555`, 75 degrees) |
| `+0xC4` | The angle the view looks along, in 65,536ths of a turn. The controls read it |
| `+0x10C`, `+0x110` | The override flag, and the override camera |
| `+0x150` | The camera this step: eye, direction `+0x15C`, roll `+0x168`, view angle `+0x16C` |
| `+0x190` | The final camera, 64 bytes |
| `+0x238`, `+0x240`, `+0x248`, `+0x26C` | The four line-test records. Results at `+0x23C`, `+0x244`, `+0x24C` |
| `+0x274` | A scripted path, when set |

## The player object

From the camera study.

| Offset | What it holds |
|---|---|
| `+0x18` | The input object |
| `+0x70` | The player's own mode: 1 ground, 2 air, 3 grind, 5 spraying |
| `+0x80` | The state the camera picks by: 0 normal, 2 big graffiti, 3 to 6 grinds and the like, 8 and 9 the poses |
| `+0x84` | The recentre flag, for one step |
| `+0xB8`, `+0x168` | Position and heading |
| `+0x294`, `+0x298` | Small tag's view on. Its two vectors are at `+0x2A0` and `+0x2AC` |
| `+0x850` | The camera object |
| `+0x854` | The point the camera's wall lines start from |
