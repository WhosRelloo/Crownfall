# Crownfall Sprite Production Specification

Version 2 · 2026-10-27 (64 px characters in 96 px cells) · Crownfall only.

The character sheets supplied so far are **visual references**: they fix the style, proportions and outfit progression (rags → gear → legend). This document defines the **production** sheets the game loads.

## 0. What exists today, and what this spec adds

**Current implementation.** Crownfall has no game code in Studio yet. The only renderer is the one specified in `Docs/Plans/2026-10-27-m1-foundation.md` (not yet built). It works like this, and this spec keeps all of it:

| Fixed by the existing (planned) renderer | Value |
| --- | --- |
| Projection | 2.5D: a camera-facing card Part (`SpriteCard`) per character, drawn through a SurfaceGui, standing on the character's feet |
| Camera | Fixed three-quarter: 40° pitch, 70 studs, FOV 20 |
| Collision body | Standard Roblox Humanoid, ~5 studs tall, hidden on every client |
| Facing | Chosen from the character's velocity in screen space; West is East mirrored |
| Placeholder art | Drawn in code from rows of palette letters: 12 × 20 sprite pixels, sheets S / N / E, poses Idle / RunA / RunB |

**What this spec adds.** The placeholder renderer loads no image files. Production sheets need three **additions** to it; the card, camera, collision and facing pipeline stay the same:

1. An image layer inside the SurfaceGui: an `ImageLabel` per layer that steps through a sheet with `ImageRectOffset` / `ImageRectSize`, `ResampleMode = Pixelated`.
2. Facing extended from 3 sheets to 8 directions (45° sectors).
3. A per-character art manifest (section 10) mapping animation names to uploaded image IDs.

Everything below marked **MUST** is a mandatory requirement; **SHOULD** is an optional improvement.

**Verified 2026-10-27 in the Crownfall place:** an `ImageLabel` with a negative `ImageRectSize` width draws its frame mirrored. So the renderer can mirror, and 5 drawn directions are enough.

## 1. Frame size and scale

| Item | Requirement |
| --- | --- |
| Frame (cell) size | **MUST be 96 × 96 px** for every humanoid sheet (male, female, all layers, all animations) |
| Character height | **MUST be 64 px** from the bottom of the feet to the top of the head (hair may add up to 4 px) when standing in Idle row S |
| Pivot (feet point) | **MUST be pixel (48, 88)**, counting from 0 at the cell's top-left corner. Feet rest on row 87; x = 48 is the centre line between the feet |
| Margins | Free space: about 20 px each side at shoulder height, 20+ px above the head, 8 px below the feet. Weapons and limbs may use it; nothing may cross the cell edge |
| World scale | 64 px = 5 studs (Roblox character height), so **1 px = 0.078 studs** and one 96 px cell is a 7.5 × 7.5 stud card. This replaces the placeholder's 0.25 studs/px |
| Pivot consistency | The pivot **MUST** stay on the same pixel in every frame of every animation, unless the motion moves the body (dodge, knockback, lunge). Then the feet move inside the cell, and the gameplay code moves the collision body by the same amount |

Why 64 px in 96 × 96 (changed from 48 px in 80 × 80 on 2026-10-27): the approved character art has more detail than 48 px can hold. 96 px cells still fit the longsword's reach, and 10 frames × 96 px = 960 px stays under Roblox's 1024 × 1024 image limit.

## 2. Sheet dimensions and layout

- **MUST:** one PNG per (rig, layer, item, animation). Examples are in section 10.
- **MUST:** rows = directions in the order of section 3; columns = frames left to right, frame 1 in the left column.
- **MUST:** no gutters, borders, labels, arrows, info panels or padding. Frame *n* in row *r* starts at x = (n − 1) × 96, y = r × 96.
- **MUST:** width = frame count × 96; height = row count × 96.
- **MUST:** at most **10 frames** per animation (960 px) and at most **8 rows** (768 px). An animation that needs more frames is split into two named animations (for example `death` and `deathloop`).
- **MUST:** every layer sheet of the same animation has exactly the same dimensions, frame count and timing as the body sheet, so one rectangle draws every layer.
- **SHOULD:** keep sheets at exactly the computed size. No power-of-two padding; Roblox doesn't need it.

## 3. Direction order (all eight)

Row order follows the order on the reference sheet:

| Row | Direction | Screen meaning | Requirement |
| --- | --- | --- | --- |
| 0 | S | Down (toward the viewer) | **MUST** draw |
| 1 | SW | Down-left | **MUST** draw |
| 2 | W | Left | **MUST** draw |
| 3 | NW | Up-left | **MUST** draw |
| 4 | N | Up (away, back to viewer) | **MUST** draw |
| 5 | NE | Up-right | Optional (mirrored from NW) |
| 6 | E | Right | Optional (mirrored from W) |
| 7 | SE | Down-right | Optional (mirrored from SW) |

- A 5-row sheet (rows 0–4): the renderer mirrors NW → NE, W → E and SW → SE.
- An 8-row sheet: the renderer uses every row as drawn. **SHOULD** be used when a design is asymmetric (a sword in the right hand ends up in the left hand when mirrored, as do side-parted hair and one-shouldered capes).
- Each direction covers a 45° sector of screen space, centred on its direction.
- **Single-facing animations** (section 4, "Rows") use only the rows listed for them, in the same order. A climbing sheet that lists N and W is 2 rows: row 0 = N, row 1 = W.

## 4. Movement animations

**Loop modes:** *Loop* repeats; *Once* plays and ends on the next state; *Hold* plays once and stays on the last frame.

The blueprint has no slide, but you asked for sliding, so it is included as pending until slide is added to the design.

| Anim id | Frames | FPS | Mode | Rows | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `idle` | 4 | 6 | Loop | 8-dir | **MUST** (P0) | Breathing, weapon held low. Only the breathing may change between frames |
| `run` | 8 | 12 | Loop | 8-dir | **MUST** (P0) | Default movement speed; contact frames 1 and 5 |
| `dodge` | 8 | 20 | Once | 8-dir | **MUST** (P0) | 0.4 s roll = 24 game frames. Frames 2–5 are the i-frames. The body travels up to ~2 studs (26 px) inside the cell; the gameplay code moves the rest |
| `walk` | 8 | 10 | Loop | 8-dir | P1 | Walk toggle / analogue |
| `sprint` | 8 | 14 | Loop | 8-dir | SHOULD | Otherwise `run` plays at 1.2× |
| `step` | 4 | 20 | Once | 8-dir | P1 | Light-armour quickstep. This is what the reference sheet calls "dash" |
| `jump` | 3 | 12 | Hold | 8-dir | P1 | Crouch, push, rise |
| `fall` | 2 | 8 | Loop | 8-dir | P1 | |
| `land` | 3 | 15 | Once | 8-dir | P1 | Roll-landing reuses `dodge` |
| `vault` | 6 | 15 | Once | 8-dir | P1 | Waist-high obstacle |
| `climbup` | 6 | 10 | Loop | N, W | P1 | Up and down (down plays in reverse) |
| `climbside` | 6 | 10 | Loop | N, W | P1 | Shimmy left and right on the wall |
| `hang` | 2 | 4 | Loop | N, W | P1 | Still on a wall or ledge |
| `mantle` | 6 | 12 | Once | N, W | P1 | Pull up over a ledge |
| `wallrun` | 6 | 14 | Loop | W | SHOULD | Runner Routes; E mirrored |
| `slide` | 6 | 14 | Hold | 8-dir | Pending design | |

Climbing has only N and W rows: with the fixed camera a climber is seen from behind or from the side, never from the front. E-side walls use W mirrored, or a third row E if the design is asymmetric.

## 5. Combat animations

Frame numbers start at 1. **Hit** marks the frame where damage is checked. Gameplay windows are authored in `Config` in seconds, and the Hit frame **MUST** match them: the Hit frame starts at (Hit − 1) ÷ FPS seconds.

| Anim id | Frames | FPS | Mode | Phase split (frames) | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `light1` | 6 | 15 | Once | windup 1–2 · active 3–4 (Hit 3) · recover 5–6 | **MUST** (P0) | Slash 1 |
| `light2` | 6 | 15 | Once | windup 1–2 · active 3–4 (Hit 3) · recover 5–6 | **MUST** (P0) | Slash 2, opposite arc |
| `light3` | 8 | 15 | Once | windup 1–3 · active 4–5 (Hit 4) · recover 6–8 | **MUST** (P0) | Finisher |
| `heavy` | 10 | 15 | Once | windup 1–5 · active 6–7 (Hit 6) · recover 8–10 | **MUST** (P0) | Frame 5 is the guard-pressure tell pose |
| `block` | 4 | 15 | Hold | raise 1–3, hold 4 | **MUST** (P0) | Holding Guard |
| `blockhit` | 3 | 15 | Once | | **MUST** (P0) | Absorbing a hit while blocking; also used for a Late Parry |
| `parry` | 4 | 24 | Once | deflect 1–2 · settle 3–4 | **MUST** (P0) | 4 frames ≈ the 0.167 s parry window; frame 2 shows the spark contact |
| `hit` | 4 | 15 | Once | | **MUST** (P0) | Light hit reaction |
| `guardbreak` | 8 | 9 | Once | | **MUST** (P0) | Player posture break, 0.9 s |
| `death` | 10 | 10 | Hold | | **MUST** (P0) | Ends lying on the ground |
| `critical` | 10 | 12 | Once | Hit 6 | P1 | Finisher on a posture-broken enemy (10-frame limit) |
| `parrywhiff` | 4 | 13 | Once | | P1 | Mistimed tap: 18-frame (0.3 s) lockout |
| `hitheavy` | 6 | 15 | Once | | P1 | Heavy-hit reaction |
| `stagger` | 6 | 8 | Loop | | P1 | Posture broken (enemies 1.5 s, bosses 2.0 s); also on players stunned by a Grab |
| `knockback` | 6 | 12 | Once | | P1 | Body slides up to ~2 studs (26 px) backward inside the cell |
| `getup` | 6 | 10 | Once | | P1 | From knockback or a downed revive |
| `downed` | 4 | 4 | Loop | | P1 | Co-op downed state (20 s) |
| `heavycharge` | 2 | 6 | Loop | | SHOULD | Holding a charged attack; release plays `heavy` from frame 6 |
| `sprintattack` | 8 | 15 | Once | Hit 4 | SHOULD | |
| `plunge` | 6 | 15 | Once | Hit 5 | SHOULD | Ledge drop attack |

**Combat rows:** every combat animation is 8-dir (5 drawn plus mirrors, or 8 drawn).

**Readability (MUST, blueprint 4.13):** every windup frame (light frame 2, heavy frame 5) is a distinct pose recognisable as a silhouette without colour. Enemies must meet this rule for every attack they own.

## 6. Transparency, resolution, outline and scaling

| Rule | Requirement |
| --- | --- |
| File format | **MUST** be 32-bit RGBA PNG |
| Background | **MUST** be fully transparent (alpha 0) |
| Character pixels | **MUST** be fully opaque (alpha 255). No partial alpha on bodies, clothing, armour or weapons |
| Anti-aliasing | **MUST NOT** be used: no soft edges, blur, smoothing or sub-pixel shading. This is the main difference from the reference sheets |
| Resolution | **MUST** be authored and exported at 1× (one art pixel = one image pixel). Never upscale before upload; the engine scales with `ResampleMode = Pixelated` |
| Outline | **MUST** be 1 px on the outer silhouette, using the darkest colour of the character's palette (not pure black, e.g. #1C1622). **SHOULD:** interior lines and selective outlining (lighter outline on lit edges) |
| Palette | **SHOULD:** at most 32 colours per character layer, using the reference sheets' earthy rag palette for starter gear |
| Light direction | **MUST** be top-left, the same in every sheet |
| Scaling | **MUST NOT** pre-scale. The game decides on-screen size (1 px = 0.078 studs) |
| VFX sheets | Exception: effect sheets (section 9) may use partial alpha |

## 7. Male and female

- **MUST:** separate sheets. Male and female are two **rigs** (`humanm`, `humanf`) with different silhouettes (shoulders, hips, hair volume), so every body and clothing sheet is drawn twice.
- **MUST:** both rigs share the same cell size, pivot, frame counts, FPS, phase splits and Hit frames, so all gameplay is identical.
- **MUST:** both rigs keep the **weapon hand at the same pixel position** in every frame. That lets one weapon sheet serve both rigs (section 9).

## 8. Unarmoured vs. armoured: layers, not separate characters

**Phase 1 (one playable character, MUST):** a single **flattened** sheet per animation, with body, rags, hair and longsword painted together (layer `full`). The renderer draws one layer. This is the quickest path to a working character.

**Phase 2 onward (MUST for character creation and progression):** interchangeable layers, drawn in matching frames and stacked bottom to top:

| Z | Layer id | Content | Per rig? | Recolour |
| --- | --- | --- | --- | --- |
| 1 | `weaponback` | Weapon parts behind the body (mostly N, NW, NE rows) | Shared | No |
| 2 | `body` | Skin and underclothes, drawn in **light greyscale** | Yes | Tinted by skin tone (`ImageColor3`) |
| 3 | `face` | Eyes, brows, scars, tattoos | Yes | No |
| 4 | `outfit` | Clothing: rags, traveller, scholar… | Yes | No; colour variants are separate items |
| 5 | `armor` | Light / medium / heavy armour pieces | Yes | No |
| 6 | `cape` | Cloaks and capes | Yes | No |
| 7 | `hair` | Hairstyle, drawn in **light greyscale** | Yes | Tinted by hair colour |
| 8 | `weaponfront` | Weapon parts in front of the body | Shared | No |

- Rags are an **outfit item** (`outfit_rags`), not a separate character. Armour hides the outfit beneath it only where it covers it, so armour sheets are drawn on top, not as full replacements.
- **Cost (be aware):** every layer item needs every animation × every drawn direction × both rigs. One outfit for the P0 list is 83 frames × 5 rows × 2 rigs = 830 frames.
- **SHOULD:** split armour into slots (chest, legs, boots, gloves) only after the full-armour sets work; each slot multiplies the drawing work.
- Greyscale tinting is a multiply, so it only darkens. Skin and hair **MUST** be drawn light (lightest tone near white) for every tint to work.

## 9. Weapons, clothing, armour and effects

- **Weapons:** drawn as `weaponback` and `weaponfront` layers on the shared rig (`shared`), one pair per weapon item per animation. The artist decides per frame which parts sit behind or in front of the body. Prototype weapon: `longsword`.
- **Clothing and armour:** layers 4–6 above, per rig, aligned pixel-perfectly to the body frames.
- **Power effects** (Shard powers, elemental strikes, slash trails, parry sparks): Crownfall has no alchemy; its equivalent is the power and VFX system (blueprint 4.7). Effects are **not** character layers. They are separate sheets drawn on their own card just in front of the character card:
  - **MUST:** use the same 96 × 96 cell and pivot when an effect is tied to a character pose (slash trail for `light1`), with the same rows, frames and FPS as that animation.
  - **MAY:** use larger cells (160 × 160, pivot at the bottom centre) for free-standing effects such as a Ward dome.
  - Partial alpha is allowed. Effects render with `LightInfluence = 0` so they glow at night.
  - Telegraph colours and shapes (white glint, amber chevron, red sigils) come from blueprint 4.4 and **MUST** be kept.

## 10. File naming and loading format

**File name (MUST, lowercase, no spaces):**

```
cf_<rig>_<layer>_<item>_<anim>.png
```

| Token | Values |
| --- | --- |
| `rig` | `humanm`, `humanf`, `shared` (weapons), later e.g. `wolf`, `banditchief`, `roadhorse` |
| `layer` | `full`, `weaponback`, `body`, `face`, `outfit`, `armor`, `cape`, `hair`, `weaponfront`, `fx` |
| `item` | `base`, `rags`, `messy`, `ponytail`, `longsword`, `traveler`, `knight`… (letters and digits only) |
| `anim` | An anim id from sections 4–5 |

Examples: `cf_humanm_full_rags_idle.png` (Phase 1), `cf_humanf_hair_ponytail_run.png`, `cf_shared_weaponfront_longsword_light1.png`, `cf_humanm_fx_slash_light1.png`.

**Repo location (MUST):** `Art/Sprites/<rig>/` holds the PNG sources, e.g. `Art/Sprites/humanm/cf_humanm_full_rags_idle.png`.

**Upload and IDs (MUST):** sheets are uploaded as Images through Studio's Asset Manager (Bulk Import) or the Creator Hub; Studio tools can't upload local files. Each resulting ID goes into `Art/Sprites/asset-ids.json`:

```json
{ "cf_humanm_full_rags_idle.png": 1234567890 }
```

**Loading format (MUST, read by the renderer addition):** one Luau manifest per rig, generated from the PNG sizes and `asset-ids.json`, at `src/ReplicatedStorage/Crownfall/Render/Art/<rig>.luau`:

```lua
return {
	Rig = "humanm",
	Cell = 96, -- px
	Pivot = Vector2.new(48, 88), -- px from the cell's top-left
	StudsPerPixel = 5 / 64,
	Anims = {
		idle = { Frames = 4, FPS = 6, Mode = "Loop", Rows = 5 },
		light1 = { Frames = 6, FPS = 15, Mode = "Once", Rows = 5, Hit = 3 },
		climbup = { Frames = 6, FPS = 10, Mode = "Loop", Rows = 2, Facings = { "N", "W" } },
	},
	Layers = {
		full = { rags = { idle = "rbxassetid://1234567890", light1 = "rbxassetid://…" } },
	},
}
```

`Rows = 5` means drawn rows S, SW, W, NW, N, with the east side mirrored; `Rows = 8` means all directions drawn. The anim ids, frame counts and FPS in this manifest **MUST** equal the tables in sections 4–5. A sheet whose pixel size disagrees with its manifest entry is rejected by the manifest tool.

## 11. Races, monsters and mounts

- **Other humanoid races** with human proportions (64 px tall) reuse the `humanm` / `humanf` animations and add race features as `face` or `hair` layer items (ears, horns, markings).
- **Different body sizes** (short or very tall races) are new rigs with their own full animation set. Same naming, format, direction order and frame rules; the cell size may change.
- **Monsters and mounts** are their own rigs. They **MUST** keep the bottom-centre pivot and direction order. Cell sizes: 96 (human-sized), 128 (wolves, horses), 192 (trolls, bosses), and 256 for dragons, whose sheets split into several files to stay under 1024 px. Each rig's animation list is written when its milestone starts (M4 for enemies).
- **Mounted riders:** a `ride` animation set on the human rigs (idle, walk, run, attack), drawn to sit on each mount rig's saddle point. Defined with mounts.

## 12. Production checklist, by priority

### P0: one playable character (male, Phase 1 flattened, longsword)

Goal: movement and core combat look right in M1–M3.

- [ ] `cf_humanm_full_rags_idle.png` (4 × 5, 384 × 480)
- [ ] `cf_humanm_full_rags_run.png` (8 × 5, 768 × 480)
- [ ] `cf_humanm_full_rags_dodge.png` (8 × 5, 768 × 480)
- [ ] `cf_humanm_full_rags_light1.png` (6 × 5, 576 × 480)
- [ ] `cf_humanm_full_rags_light2.png` (6 × 5, 576 × 480)
- [ ] `cf_humanm_full_rags_light3.png` (8 × 5, 768 × 480)
- [ ] `cf_humanm_full_rags_heavy.png` (10 × 5, 960 × 480)
- [ ] `cf_humanm_full_rags_block.png` (4 × 5, 384 × 480)
- [ ] `cf_humanm_full_rags_blockhit.png` (3 × 5, 288 × 480)
- [ ] `cf_humanm_full_rags_parry.png` (4 × 5, 384 × 480)
- [ ] `cf_humanm_full_rags_hit.png` (4 × 5, 384 × 480)
- [ ] `cf_humanm_full_rags_guardbreak.png` (8 × 5, 768 × 480)
- [ ] `cf_humanm_full_rags_death.png` (10 × 5, 960 × 480)
- [ ] All 13 uploaded, IDs in `Art/Sprites/asset-ids.json`

Total: 83 frames per direction × 5 drawn directions = **415 frames**.

**Start with one sheet:** before the other 12, make `idle` and test it in the game. That confirms the size, pivot and scale.

### P1: the full prototype (blueprint 13.1)

- [ ] Same rig/layer: `walk`, `step`, `jump`, `fall`, `land`, `vault`, `critical`, `parrywhiff`, `hitheavy`, `stagger`, `knockback`, `getup`, `downed`
- [ ] Climbing set (N, W rows): `climbup`, `climbside`, `hang`, `mantle`
- [ ] Effects: `cf_humanm_fx_slash_light1/2/3`, `cf_humanm_fx_slash_heavy`, `cf_shared_fx_parryspark_parry`
- [ ] First enemy rig (Swordsman) idle/run/attacks/stagger/death, specified in M4

### P2: character creation (both bodies, layered)

- [ ] `humanf` P0 + P1 sets
- [ ] Split both rigs into layers: `body_base` (greyscale), `face_base`, `hair_<style>` ×3 to start (greyscale), `outfit_rags`, `weaponback/weaponfront_longsword` (shared)
- [ ] Skin-tone and hair-colour tint palettes (5 each) tested in game

### P3: progression and world

- [ ] Outfits (traveller, merchant, scholar, hunter, noble, street) per rig
- [ ] Armour sets (light, medium, heavy, knight, assassin, special) per rig
- [ ] Weapon families: sword & shield, spear, greatblade, twin fangs, lantern catalyst (shared rig)
- [ ] `wallrun`, `sprint`, `sprintattack`, `plunge`, `heavycharge`; `slide` once it is in the design
- [ ] Races, monster rigs, mount rigs and `ride` sets, per milestone

## 13. Open items

- [ ] Decide whether slide joins the Crownfall design (blueprint 4.10 has no slide).
- [ ] Confirm the 64 px character height in the game with the first `idle` test sheet.
