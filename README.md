# Crownfall

A multiplayer 2.5D pixel-art action RPG for Roblox, built around parrying, dodging and posture combat.

> Status: design phase. No game code yet.

## Documents

- [Game Design Blueprint](Docs/Design-Blueprint.md): high concept, combat and movement, world and story, multiplayer, mounts, economy, presentation, UI, prototype plan, roadmap, risks and open decisions.

## Key decisions so far

- **Engine:** Roblox Studio.
- **Rendering:** the whole game is 2.5D: pixel sprites in a 3D collision world with a fixed three-quarter camera.
- **First milestone:** a combat and movement prototype ("The Shrine Yard") that must pass the feel gate before anything else is built.

## Working on the code

The repo is the source of truth; Studio is a build target. Open the **Crownfall** place (placeId 93979562442002) in Studio in Edit mode, then from the repo root:

- `python -I Tools/studio.py sync` pushes `src/` into the place. It rebuilds every `Crownfall` folder, so never edit those scripts in Studio.
- `python -I Tools/studio.py test` runs every spec in `ServerStorage.Crownfall.Tests`.
- `python -I Tools/studio.py luau Client @Tools/checks/m1_play.luau` (during Play) checks the camera and sprites.
- `python Tools/sprites.py` converts a large painted sheet into a spec sheet (see `Docs/Art-Spec.md`).

Plans for each milestone live in `Docs/Plans/`.
