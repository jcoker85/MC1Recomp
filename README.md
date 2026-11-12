# MC1Recomp

Midnight Club: Street Racing (PS2, 2000) as a native Windows program, built with
[ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp) from your own disc, with a launcher and a set of
optional improvements: widescreen, 60 FPS, higher resolutions, upscaling, and more. A sister project of
[MC2Recomp](https://github.com/jcoker85/MC2Recomp), whose launcher and toolkit changes it reuses.

| Game | Disc | Serial |
|---|---|---|
| Midnight Club: Street Racing | USA | SLUS-20063 (program CRC DFD26C76) |

This is an unofficial fan project. It is not affiliated with or endorsed by Rockstar Games, Take-Two Interactive or Sony
Interactive Entertainment.

## Play

You need your own disc image of Midnight Club: Street Racing (USA) as an `.iso`. The game is on a CD, so a `.chd` is
unpacked with MAME's chdman:
`chdman extractcd -i "Midnight Club.chd" -o "Midnight Club.cue" -ob "Midnight Club.iso"`. If the `.cue` it writes says
`MODE1/2048`, the `.iso` is ready. If it says `MODE1/2352` or `MODE2/2352` (a raw dump), convert it with the toolkit:
`python ps2-native-recomp/scripts/disc.py iso "Midnight Club.cue" "Midnight Club.iso"`.

Windows 10 or 11 (64-bit), a CPU with AVX2 and a Direct3D 12 graphics card.

1. Run `MC1Recomp.exe` (build it first, below).
2. Press **Play**. The first time, it asks for your disc image; the launcher remembers it
   (**Settings > Disc Image** changes it).
3. **Settings** has three tabs: **Graphics**, with the options below, **P1 Controls** and **P2 Controls**. Every option
   starts off, so a fresh install plays the game as it is on a PS2.

### Options

- **Fullscreen**, **Resolution** (1x to 4x the PS2's), **Vsync**, **Frame Pacing Fix** (frames on an even 59.94 Hz clock)
- **Picture Mode**: how the picture is enlarged to the window: Crisp, Soft or Sharp, each with optional edge smoothing,
  or **FSR** (AMD FidelityFX Super Resolution 1)
- **Texture Filtering**: the game's own (Bilinear PS2), Nearest, or Bilinear (Forced)
- **60 FPS** (the PCSX2 community patch by asasega): the game's frame interval kept at one vsync
- **Widescreen** 16:9 (the PCSX2 community patch by PeterDelta, with its own aspect on the car select screen), **Fixed
  Widescreen HUD** (the driving HUD keeps its 4:3 shapes at the screen's edges: map, timer, position, speedometer,
  damage), **Menu/Movie Aspect Ratio** (menus, loading screens and videos in 4:3 while driving is 16:9)
- **Color Settings**: the PS2's 16-bit picture, or the game's full 32-bit picture; **Dithering** (the PS2's dither on the
  16-bit picture)
- **Smooth Distant Textures** (less shimmer on far buildings; not something a PS2 does)

MC2Recomp's Skip Intro needs a switch in the game's own code that Midnight Club does not seem to have, so the launcher does
not show it.

The game's split-screen 2-player cruises and races work: set **Players** to **Two** on the race setup screen (connect two
controllers, or play player 1 on the keyboard and player 2 on a controller). Widescreen, the fixed HUD and 60 FPS work in
both halves. Career saves go to the memory card file in `ps2-native-recomp/games/mc1` (the game offers to format it the
first time).

**P1 Controls** and **P2 Controls** work as in MC2Recomp: choose Controller or Keyboard (with the mouse) for player 1 and
rebind every PS2 button and stick direction; the bindings are kept in `ps2-native-recomp/games/mc1/keys.ini`.

## Build

On Windows, with Git for Windows (Git Bash), CMake, Ninja, Python 3 and llvm-mingw (UCRT). The toolkit's
`scripts\bootstrap.ps1` installs them with winget; no Visual Studio is needed.

```bash
git clone --recursive https://github.com/jcoker85/MC1Recomp.git
cd MC1Recomp
bash tools/build.sh "/c/Games/Midnight Club - Street Racing (USA).iso"
```

`tools/build.sh`:

1. fetches ps2-native-recomp v0.0.4 (the submodule) and applies `patches/ps2-native-recomp.patch`;
2. sets up the toolkit's build tools;
3. translates the game's code from your disc into C++ and builds the game program (`ps2run.exe`);
4. downloads the launcher's icon (`tools/make_icon.ps1`; any square PNG at `hub/icon/hub.png` is used instead) and builds
   the launcher, `MC1Recomp.exe`, whose icon the game window shows too.

The first build takes a while. Code the first build did not see is translated while you play and kept for next time.

## What is and is not in this repository

The repository holds the launcher, patches, build files and documentation. It does **not** contain disc images, the game's
program, game assets, cover art or recompiled game code. The recompiled C++ and the game program are generated on your
machine from your own disc and stay in `ps2-native-recomp/generated` and `ps2-native-recomp/games`, which git ignores. When
the game runs, it reads its data from your disc image.

- `hub/`: the launcher (`hub.c`, MC2Recomp's launcher with Midnight Club's options) and its build files.
- `mc1-options/`:
  - `widescreen.txt` and `60fps.txt`: the PCSX2 community patches (Widescreen 16:9 by PeterDelta, 60 FPS by asasega) as
    `ps2run --patches` lines. The launcher copies the lines of the options that are on into `boot.txt` at each start.
  - `menus43.txt` / `widescreen43.txt`: Menu/Movie Aspect Ratio. The game's flag at `0x2C3C78` (1 only while driving) picks
    the picture's shape each frame, and the widescreen patch writes the game's own values back while it is 4:3.
  - `hud43.py` / `hud43.pnach`: the code behind Fixed Widescreen HUD (the same method as MC2Recomp's): hooks on the draw
    calls of the game's HUD (`0x125C78`) mark each part in the game's VIF1 packets, and the runtime squeezes what a marked
    part draws toward its edge. It is built into the game program and switched by a word the launcher writes.
- `patches/ps2-native-recomp.patch`: this project's changes to the toolkit: MC2Recomp's (the fixes Midnight Club II
  needed to run, which the engine shares, dithering, texture filtering, smooth distant textures, FSR, keyboard and
  controller bindings, two players), plus two for Midnight Club:
  - conditional patch lines (`3 ADDRESS N VALUE`: the next N lines apply only while the 16-bit value at ADDRESS is VALUE,
    PCSX2's `E0` code), which the widescreen patch uses;
  - idle sound-chip voices report that they have ended (ENDX), as on the real chip, where a voice keeps running through
    sound memory after key-off. The game's sound driver only gives a sound a voice that has ended, so without this the
    title screen and menus had no music or sound effects;
  - speed: the vector unit interpreter goes on in compiled code after a jump (two of the game's busiest VU1 programs start
    with a branch in a branch's delay slot, which only the interpreter runs: 17 % of the game's thread), and Smooth
    Distant Textures reads 4x fewer texels (single-texel taps, only past 1.5 texels a sample);
  - the HUD squeeze's frame width (`PS2_HUD_WIDTH`, 640 here; MC2's frame is 512);
  - the picture height of interlaced frame mode (SMODE2 INT=1, FFMD=1) counts both fields, as PCSX2 reads it: the intro
    movies (a 640x448 window of 720x480 frames) showed 480 lines, 32 of them empty memory under the picture;
  - at higher resolutions, a texture the game drew itself (the cars' reflection map) is read at the sample under the texture
    position instead of the screen pixel's own: the screen position made a 4-pixel screen-door grid over the cars at 4x;
  - scripted presses for the second controller (`--press 100:p2cross`, used to test the 2-player races);
  - fair interrupt turns: pending DMAC channels are served in rotation, alternating with the INTC. A stream of instant VIF1
    transfers kept channel 1 pending, so the SIF0 interrupt (the IOP's replies) waited for frames, and the game, blocked in
    its rumble and sound calls, fell to about 10 frames a second while scraping a wall.
- `ps2-native-recomp/`: the toolkit, as a git submodule.
- `tools/`: the build script, the release packaging script, the icon script and `mips.py` (a small R5900 disassembler and
  address-reference finder used to trace the game's code).

## Credits

- [ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp) by Samir Nuri and exoteric33 (MIT): the
  recompiler and runtime this project is built on.
- The PCSX2 community patches (from [PCSX2/pcsx2_patches](https://github.com/PCSX2/pcsx2_patches)): Widescreen 16:9 by
  PeterDelta, 60 FPS by asasega.
- AMD FidelityFX Super Resolution 1.0 (MIT, Copyright (c) 2021 Advanced Micro Devices, Inc.): the FSR picture mode is
  written after AMD's published shaders.
- Box art in the launcher: [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails).
- The launcher and game window icon: [Midnight Club: Street Racing icon by r_dsgnd](https://www.steamgriddb.com/icon/119111)
  on SteamGridDB, downloaded at build time.

## License

MIT; see `LICENSE`. ps2-native-recomp is MIT as well.

Midnight Club is a trademark of Take-Two Interactive Software, Inc., and the game is copyright its owners. This repository
contains none of its code, data or artwork, nor the icon and box art the launcher downloads.

## AI disclosure

This project was built with Claude (Anthropic) working as a coding assistant under the direction of the author.

- **Claude did:** ported MC2Recomp's launcher, build and packaging scripts to this game, added the conditional patch lines
  to the toolkit, turned the PCSX2 patches into launch-time options, traced the game's code for the addresses involved, and
  drafted this README.
- **Claude did not:** write ps2-native-recomp, which is another project used here as a submodule, the PCSX2 community
  patches, or the game itself, whose code the recompiler translates from your own disc.
