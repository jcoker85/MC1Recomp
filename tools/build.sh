#!/usr/bin/env bash
# Builds MC1Recomp from your own Midnight Club: Street Racing (USA) disc image, in Git Bash on Windows.
#
#   bash tools/build.sh "/c/Games/Midnight Club - Street Racing (USA).iso"
#
# (a .cue/.bin CD dump works too: the toolkit cuts it down to an .iso in ps2-native-recomp/games/mc1/disc.iso)
#
# 1. fetches ps2-native-recomp (the submodule, v0.0.4) and applies this project's changes to it (patches/);
# 2. sets up the toolkit's build tools (its scripts/setup.sh);
# 3. translates the game's code from your disc into C++ and builds the game program (the toolkit's scripts/port.sh), with the
#    Fixed Widescreen HUD's hooks (mc1-options/hud43.pnach, made by mc1-options/hud43.py; off until the launcher turns it on);
# 4. builds the launcher, MC1Recomp.exe, in this folder (with an icon if tools/make_icon.ps1 finds one).
# The widescreen / 60 FPS / 4:3 menus options (mc1-options/) are memory patches and runtime settings the launcher hands the
# game at start, so they need no rebuild. Everything taken from the disc stays in ps2-native-recomp/games and ps2-native-recomp/generated, which git ignores.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
iso=${1:-}
if [ -z "$iso" ] || [ ! -f "$iso" ]; then
  echo "usage: bash tools/build.sh <your Midnight Club: Street Racing (USA) disc image: .iso, or .cue/.bin>" >&2
  exit 2
fi
iso=$(cd "$(dirname "$iso")" && pwd)/$(basename "$iso")

cd "$here"
git submodule update --init ps2-native-recomp
cd ps2-native-recomp
patch=../patches/ps2-native-recomp.patch
if git apply --check "$patch" 2> /dev/null; then
  git apply "$patch"
  echo "applied $patch"
elif git apply --reverse --check "$patch" 2> /dev/null; then
  echo "$patch is already applied"
else
  echo "ps2-native-recomp has changes that are not $patch: set it back (git -C ps2-native-recomp checkout .) and run again" >&2
  exit 1
fi

bash scripts/setup.sh --native-only
bash scripts/port.sh mc1 "$iso" --native-only \
  --pnach ../mc1-options/hud43.pnach --pnach-section "HUD 4:3"

cd "$here"
powershell -NoProfile -ExecutionPolicy Bypass -File tools/make_icon.ps1
cmd //c "hub\\build.cmd"
echo
echo "Done: run MC1Recomp.exe, press Play and choose your disc image (an .iso)."
