# Crownfall Character Customization: Research and Plan

2026-10-27 · Crownfall only.

**Recommendation in one line:** build customization in two layers of effort. First, **recolour** the art we already have (skin, hair, outfit, eye and Brand colours) at runtime. Then add **swappable parts** (hairstyles, outfits, female body) as separately drawn layers. Wrap both in a creator that follows the pattern players rate best: **curated presets you can then edit, a randomize button, and a large, animated live preview**.

---

## 1. What the research says

### How pixel-art games do customization

| Technique | What it changes | Cost | Used by |
| --- | --- | --- | --- |
| **Palette swap**: replace a fixed set of colours (a "ramp") with another set | Colours only: skin, hair, cloth, eyes | One sprite set serves endless colour variants | Classic NES/SNES games, Terraria, Starbound |
| **Layered sprites**: separate drawings for body, hair, clothes and weapon, stacked at runtime | Shapes: hairstyles, outfits, armour, gear | Every layer needs every frame of every animation, in every direction | Stardew Valley, the LPC sprite generator, Soulbound |
| **Hybrid**: layers for shapes, palette swaps for colours | Both | Shapes cost art; colours are free | The most common approach in shipped games |

Key lessons:
- **Palette swapping hair and skin in code** gives "endless versions while only using one set of sprites". Hair and skin each need their own **ramp** (a small set of shades ordered dark to light), kept separate from each other. ([Solarus forum](https://forum.solarus-games.org/en/index.php/topic,1324.0.html), [pixel-art ramp discussion](https://itch.io/post/14616073), [GameDev.net on colour ramps](https://www.gamedev.net/articles/visual-arts/color-palettes-r4964/))
- **Ramps should shift hue, not only brightness.** Hair ramps need enough contrast against skin, and palettes need browns for hair and skin. ([GameDev.net](https://www.gamedev.net/articles/visual-arts/color-palettes-r4964/), [Pixel Joint forum](https://pixeljoint.com/forum/printer_friendly_posts.asp?TID=20269))
- **Starbound** recolours hair by replacing three base colours on the sprite, with separate colour groups for body, hair and underclothes. Facial hair is its own layer. A "personality" choice sets the idle pose. ([Starbound modding guide](https://community.playstarbound.com/threads/a-guide-on-implementing-character-customization-for-custom-races.136565/), [Starbounder](https://starbounder.org/Guide:Getting_Started))
- **Layered gear (Soulbound devlog):**
  - Each cosmetic must be hand-drawn to fit, and all cosmetics share one palette.
  - Every gear set must have the same frame count per animation, so the base run cycle was locked early.
  - Layer order changes with facing direction and weapon.
  - The main cost is the combinations: weapons × animations × directions × slots.

  ([Soulbound](https://soulbound.game/news/how-we-built-a-pixel-art-character-and-cosmetic-system/))
- **LPC Universal Spritesheet Generator:** the best-known open layered system. It merges around 27 ordered layers, and weapons use separate front and back layers. Layer order matters. ([LPC generator](https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator), [lpcg](https://lib.rs/crates/lpcg))

### What players and other games offer

| Game | Options |
| --- | --- |
| **Stardew Valley** | 24 skin tones, 74 hairstyles, 112 shirts, 4 pants, 31 accessories; appearance can be changed later at a shrine. ([Stardew wiki](https://stardewvalleywiki.com/The_Player)) |
| **Terraria** | Hair, hair colour, clothing style with separate shirt / undershirt / pants / shoes colours, skin and eye colour; HSV colour bars; a Stylist NPC changes hair later. ([Terraria wiki](https://terraria.wiki.gg/wiki/Character_styles)) |
| **Octopath Traveler 0** (pixel sprites in a 3D world, like Crownfall) | Physique, eye colour, hairstyle and colour, 6 skin tones, a choice of 3 "motions" (idle personality) and 6 voices; at sprite size, eye colour is "a literal pixel". ([character creation guide](https://hacktheminotaur.com/octopath-traveler-0/octopath-traveler-0-character-creation-ultimate-guide/), [hands-on preview](https://onemoregame.ph/2025/09/octopath-traveler-0-hands-on-preview/)) |

**Presets vs sliders:** players split, but the most-praised creators combine both. Monster Hunter Wilds is cited for letting you pick from a list *and then edit from there*. Artist-made presets get a good-looking result fastest, and pure presets risk NPCs who look like your twin. ([RPGHQ discussion](https://rpghq.org/forums/viewtopic.php?p=227359))

### What Roblox allows (decides the technical approach)

| Tool | What it can do | Limits |
| --- | --- | --- |
| `ImageLabel.ImageColor3` | Multiplies a whole image by one colour (tint) | Only darkens and only one colour per image, so it needs art drawn light and grey, one layer per tinted part. ([ImageLabel docs](https://create.roblox.com/docs/reference/engine/classes/ImageLabel)) |
| `EditableImage` | Read and rewrite individual pixels on the player's machine: true palette swaps | Off by default in published games. The **owner must be 13+ and ID-verified** and turn on **Enable Mesh / Image APIs**. Max 1024×1024 each. Client memory budget is strict. ([EditableImage docs](https://create.roblox.com/docs/reference/engine/classes/EditableImage), [DevForum](https://devforum.roblox.com/t/remove-required-id-verification-for-editablemeshesimages/3981479)) |
| `AssetService:CreateDataModelContentAsync` (May 2026) | "Bakes" an edited image into fixed content | Baked content **does not use the Editable memory budget**, so we can recolour once and bake. ([DevForum announcement](https://devforum.roblox.com/t/full-release-introducing-createdatamodelcontent-convert-editable-mesh-and-image-data-into-static-content/4541898)) |

---

## 2. What this means for Crownfall

Our animations are built by `Tools/walk_cycle.py` from **one flattened drawing per direction**: body, rags, hair and sword are all in one image. That shapes the plan:

1. **Colours: possible now, with the art we have.** We know which pixels are skin, hair, cloth, leather and steel, because the tool already labels parts and the colours separate cleanly. The tool can write a **colour-index map** next to each sheet. In game, `EditableImage` repaints each sheet with the player's chosen ramps once at load, bakes it, and plays it like any other sheet. The only requirement is for you, as the place owner, to be ID-verified and turn on the Mesh / Image APIs toggle.
2. **Shapes: need the art in layers.** Hairstyles, outfits, armour and a female body need the base drawing split into separate images per direction: body, hair, outfit, weapon. Once they are split, the same tool animates every layer with identical motion, so they line up frame for frame, exactly as Soulbound and the LPC generator require. Section 8 of `Docs/Art-Spec.md` already defines these layers.

---

## 3. The plan

### Phase A: colour customization on today's art

| Option | Choices | How |
| --- | --- | --- |
| Skin tone | 8 ramps, light to deep, hue-shifted | Palette swap |
| Hair colour | 12 ramps (black, browns, auburn, red, blonde, ash, white, plus 3 fantasy) | Palette swap |
| Eye colour | 8 | Palette swap (1–2 px; visible in the creator portrait) |
| Outfit colour | 10 dyes for the rags; leather stays its own ramp | Palette swap |
| Brand mark | 4 placements × 8 glow colours (blueprint 5.1) | Small glow layer drawn on top |
| Idle personality | 3 idles: steady, restless, guarded (Octopath "motions", Starbound "personality") | Extra idle sheets later; ships with 1 |

**Rules:**
- **Curated ramps only, no free RGB picker.** This keeps every combination in palette and good-looking (art spec section 6).
- **Every ramp has the same number of shades as the colour it replaces,** so shading never breaks.
- **Checks:** a test checks every ramp swap against the audit rules, and every frame of every animation is checked with the extreme combinations (lightest and darkest skin with each hair colour).

### Phase B: swappable parts (needs layered art)

| Part | Launch target | Later |
| --- | --- | --- |
| Body | Male, female (blueprint: 4 frames × 3 heights later) | More body types |
| Hairstyles | 8 per body | +2 per update |
| Outfits | Rags (starter) + 3 origin outfits | Outfit and armour sets from progression |
| Facial hair / scars / tattoos | 4 each | — |
| Weapon | Longsword (other families with combat) | 6 families |

Each part is one layer, animated by the same tool, recoloured by the same ramps.

### The creator screen

Before the opening cutscene, as the blueprint says.

- **Large live preview, centre:** the character in your game's real lighting, playing idle, with buttons to turn through all 8 directions and to preview walk, sprint and dodge.
- **Presets first:** 8 artist-made looks to pick from, then **edit anything from there**, the Monster Hunter Wilds pattern players liked.
- **Randomize** all, or one category.
- **Swatch rows, not sliders:** each ramp shows as one swatch. For pixel art, swatches beat HSV bars because every choice is guaranteed to look right.
- **Origin choice** (blueprint 5.2) on the same screen, showing its starting outfit.
- **Name and confirm.**
- **Changing it later:** a Barber (hair and colours) and a Tailor (outfit dyes) in towns, like Stardew's shrine and Terraria's Stylist. The Brand stays fixed (it's story-bound).

**Saving:** choices are stored as a small table of ids (`{skin = 3, hair = "messy", hairColour = 7, ...}`) in the player's save. Other players' clients recolour from those ids, so everyone sees everyone else's look.

---

## 4. Phase A: what is built (2026-10-27)

**In the game now**
- **Creator screen** (`CharacterCreator.client`). It opens on first join and C reopens it until the Barber and Tailor exist.
  - 8 presets, randomize all, and a Roll button per row.
  - Body choice. Female is shown but locked until her art is in (section 5).
  - Swatches: 8 skin, 12 hair, 11 outfit (undyed + 10 dyes).
  - A 4× live preview that turns through all 8 directions and plays idle, walk, sprint and dodge.
  - Begin / Save look and Cancel. The character stands still while it is open.
- **Saving and sharing** (`Appearance.server`). The look is saved in the `CrownfallAppearance_v1` DataStore as one short string (`m:tan:copper:linen`). It rides on the Player as the `Appearance` attribute, so every client paints every player the same way.
- **Recolouring** (`Render/Recolour`).
  - Each image is downloaded once and its pixels kept.
  - For each look, each image is repainted with an EditableImage and baked with `CreateDataModelContentAsync`, then the EditableImage is freed.
  - Measured in Studio: about 3.8 s for the first look (downloads), then about 1 s for each further look (25 images).
  - The drawn image shows until its painted copy is ready.

**How a pixel knows what it is**
- `Tools/colour_classes.py` sorts each pixel of the base drawings into one of six classes:

  | Class | Recoloured? |
  | --- | --- |
  | outline | no |
  | steel | no |
  | skin | yes |
  | hair | yes |
  | outfit | yes |
  | boots | no |

- `walk_cycle.py --classes` carries the class through every move in the pixel's alpha byte. That gives a class map for walk, run and dodge that lines up exactly with the uploaded sheets. The build checks the sheets come out byte-identical, so nothing needs re-uploading.
- The uploaded idle sheet isn't in the repo, so the game classifies it itself from colour and height bands (`ClassMap.ClassifyUpright`). That works because the idle stands upright.

**How a pixel is repainted**
- Its brightness, placed within its class's range, picks a point along the chosen 5-stop ramp, so the original shading is kept.
- Outfit dye fades out on saturated pixels, so leather straps, belts and bracers keep their colour.
- `Tools/recolour.py` does the same maths in Python for previews. A spec checks the Luau and Python results agree.

**Changed from the plan**
- **Eye colour is dropped.** The eyes sit in shadow under the hair and aren't visible at sprite size.
- **The Brand mark comes next.** It needs a small glow layer placed per direction.
- **Origin and name** wait for the story systems.

**Rebuilding the data**
- After changing `Art/Sprites/palettes.json` or any walk/run/dodge art, run `python Tools/class_maps.py`.

## 5. Female body (drawn 2026-10-28)

`Tools/female.py` draws the female starter from the male base poses, one per drawn direction: S, SW, W, NW and N. The east side is mirrored. Each change is a hand-placed pixel overlay. The male drawing is painted rather than palette-limited, so the overlays use a few hair tones with a little seeded variation, and shade by darkening or brightening the pixels already there.

What makes her read as female at 64 px:

| Direction | Changes |
| --- | --- |
| Front (S, SW) | Long hair falling over the shoulders and framing the face; lips; sloped shoulders; a waist pulled in 1 px; hips out 1 px |
| Side (W) | Long hair down the back; lips in profile; a chest curve; a narrower waist; hips out |
| Back (N, NW) | Long hair over the upper back, tapering to a point |

How she is built:
- `walk_cycle.py --prefix cf_human_f_full_rags_walk` animates her idle (a new 8-frame breathing style), walk, sprint and dodge with the same motion as the male.
- `female.hair_pixels` tells the class maps that the long hair is hair, so hair colours recolour all of it.
- `python Tools/class_maps.py` rebuilds both bodies and checks each sheet against `Art/Sprites/<rig>`. `--write-female` rewrites hers after a deliberate art change.

**Audits:** idle, walk, sprint and dodge each pass `walk_audit.py` on 64/64 frames. Every frame is one connected piece, and I reviewed all of them by eye.

**Uploads:**
- `Tools/export.py` writes FIdle, FWalk, FRun and FDodge to `Downloads/Crownfall`, as `FWalk (South).png` and so on.
- Once those are uploaded, `Render/Art/humanf.luau` gets their IDs, and the Female button unlocks by itself.

## 6. Decisions needed from you

1. ~~ID verification~~: done. The Mesh / Image APIs are on.
2. **Layered art:** for hairstyles, outfits and a female body, can your art pipeline produce each direction as **separate images**: body (skin + underclothes), hair, outfit, weapon? These must be on the same 96 px grid with the same pose. I'll write the exact layer spec for the artist or generator.
3. **Launch scope:** is the Phase A + B list above the right size, or do you want more or fewer options?

## Sources

- [How We Built A Pixel Art Character and Cosmetic System (Soulbound)](https://soulbound.game/news/how-we-built-a-pixel-art-character-and-cosmetic-system/)
- [Ways to think about sprites for character customization (Solarus forum)](https://forum.solarus-games.org/en/index.php/topic,1324.0.html)
- [Pixel-art palette/ramp discussion (itch.io)](https://itch.io/post/14616073)
- [Color Palettes (GameDev.net)](https://www.gamedev.net/articles/visual-arts/color-palettes-r4964/)
- [Pixel Joint palette forum](https://pixeljoint.com/forum/printer_friendly_posts.asp?TID=20269)
- [Universal LPC Spritesheet Character Generator](https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator)
- [lpcg layer merging](https://lib.rs/crates/lpcg)
- [Starbound custom race customization guide](https://community.playstarbound.com/threads/a-guide-on-implementing-character-customization-for-custom-races.136565/)
- [Starbounder: Getting Started](https://starbounder.org/Guide:Getting_Started)
- [Stardew Valley wiki: The Player](https://stardewvalleywiki.com/The_Player)
- [Terraria wiki: Character styles](https://terraria.wiki.gg/wiki/Character_styles)
- [Octopath Traveler 0 character creation guide](https://hacktheminotaur.com/octopath-traveler-0/octopath-traveler-0-character-creation-ultimate-guide/)
- [Octopath Traveler 0 hands-on preview](https://onemoregame.ph/2025/09/octopath-traveler-0-hands-on-preview/)
- [RPGHQ: presets vs sliders discussion](https://rpghq.org/forums/viewtopic.php?p=227359)
- [Roblox EditableImage reference](https://create.roblox.com/docs/reference/engine/classes/EditableImage)
- [Roblox ImageLabel reference](https://create.roblox.com/docs/reference/engine/classes/ImageLabel)
- [DevForum: ID verification for Editable APIs](https://devforum.roblox.com/t/remove-required-id-verification-for-editablemeshesimages/3981479)
- [DevForum: CreateDataModelContentAsync](https://devforum.roblox.com/t/full-release-introducing-createdatamodelcontent-convert-editable-mesh-and-image-data-into-static-content/4541898)
