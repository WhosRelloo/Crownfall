# Character Creation: Class, Origin, Traits, Hairstyles

2026-10-28 · Approved by the owner ("Yes. Continue"). Extends `Docs/Character-Customization.md`.

**Goal:** at creation, the player picks:
- a **class**: a starting role, switchable at shrines;
- an **origin**: the kingdom they come from and spawn in;
- **2 starter traits**: small sidegrades;
- a **hairstyle**: 12 per body, drawn in-house.

It all lives in the existing creator, keeps the design doc's rules, and works for both bodies.

## 1. Rules carried over from the design doc

- **No locked classes.** A class is a starting kit and role identity; it can be switched at any shrine (blueprint 5).
- **Skill beats stats.** Traits are small, and every trait pays for its upside.
- **Origins set a start, not a fate.** The real faction pledge stays at the end of Chapter 2 (blueprint 3).

## 2. Classes (Shared/Classes.luau)

| Id | Class | Weapon | Armour | First power | Discipline | Role |
| --- | --- | --- | --- | --- | --- | --- |
| duelist | Duelist | Longsword | Medium | Oath Riposte | Striker | Balanced; wins by parrying |
| vanguard | Vanguard | Sword & Shield | Heavy | Rallying Cry | Vanguard | Holds the line, protects allies |
| lancer | Lancer | Spear | Medium | Thrust Deflect | Vanguard | Spacing; sweeps groups; mounted bonus |
| breaker | Breaker | Greatblade | Heavy | Sundering Blow | Breaker | Trades hits to crush posture |
| striker | Striker | Twin Fangs | Light | Cinder Edge | Striker | Fast, evasive, bleeds |
| warder | Warder | Lantern Catalyst | Light | Lantern Ward | Warder | Casts, cleanses, supports |

Today only the longsword is drawn and combat isn't built. So the class is saved, shown on its card, and readable by later systems, but every class visibly holds the longsword until each weapon's art and moves arrive with combat.

## 3. Origins = kingdom spawn (Shared/Origins.luau)

| Id | Origin | Homeland | Start | Standing | Starting item |
| --- | --- | --- | --- | --- | --- |
| varrow | Varrow Squire | Crown of Varrow | Highland garrison | +Varrow, −Thornborn | Squire's signet |
| compact | Compact Caravaneer | The Ashen Compact | Salt-road convoy | +Compact, −Varrow | Trade map of the Ashmarch |
| lantern | Lantern Novice | Order of the Quiet Lantern | Abbey infirmary | +Lantern, −Choir | Novice's lantern charm |
| thornborn | Thornborn Exile | The Thornborn | Forest-edge camp | +Thornborn, −Varrow | Antler fetish |
| roadborn | Roadborn Orphan | Roadwardens (neutral) | Waystation | +Roadwardens | Courier's satchel |

- **Spawn:** after the opening, and as the default respawn, the player stands at `workspace.CrownfallOriginSpawns.<id>` when that part exists. Otherwise they use the origin's default position. Regions aren't built, so these are placeholders the owner can move.
- **Fixed:** the origin can't be changed after creation.

## 4. Traits: pick 2 of 16 (Shared/Traits.luau)

Each trait changes exactly one stat for the better (**Up**) and one for the worse (**Down**). Each change is at most 25% of the stat's base value; a spec enforces both rules.

Stats are named in one registry, with their base value and which direction is better. `Traits.Value(stat, traitIds)` returns the player's value. Stamina, posture, parry and durability read it when they are wired into play in M2/M3. Stats for systems not yet built are stored and apply when those systems arrive.

| Id | Trait | Up | Down |
| --- | --- | --- | --- |
| light_footed | Light-footed | Dodge 22 stamina (25) | +10% posture taken when blocking |
| iron_grip | Iron Grip | −15% posture taken when blocking | Dodge 28 stamina |
| second_wind | Second Wind | Stamina regen starts after 0.45 s (0.6) | Max stamina 92 (100) |
| deep_lungs | Deep Lungs | Max stamina 110 | Stamina regen 36/s (40) |
| hawk_eyed | Hawk-eyed | Parry window 11 frames (10) | Missed-parry recovery 22 frames (18) |
| steady_hand | Steady Hand | Late-parry window 5 frames (4) | Perfect parry gives 16 Resolve (20) |
| thick_skinned | Thick-skinned | −8% damage taken | −10% Resolve gained |
| quick_recovery | Quick Recovery | Guard Broken 0.75 s (0.9) | Posture decays 18/s (20) |
| unshaken | Unshaken | Posture decay starts after 1.2 s (1.5) | +5% damage taken |
| fleet | Fleet | Sprint 10 stamina/s (12) | Climb 10 stamina/s (8) |
| climber | Climber | Climb 6 stamina/s (8) | Sprint 14 stamina/s (12) |
| tinker | Tinker | −20% gear wear | Repairs cost +15% |
| haggler | Haggler | Shop prices −8% | Quest gold −5% |
| hardy | Hardy | Ailment build-up −20% | Tonic healing −10% |
| battle_born | Battle-born | +20% Resolve from landed hits (3→3.6) | Resolve fades 25% faster out of combat |
| beast_friend | Beast-friend | Mount bond grows 20% faster | Bandits notice you 10% sooner |

**Trait rules:** exactly 2, they must be different, and they are fixed after creation.

## 5. Hairstyles (12 per body)

- **Male:** Messy (current), Cropped, Undercut, Swept Back, Long Loose, Tied Back, Topknot, Braids, Mohawk, Buzz, Shaved, Curly.
- **Female:** Long (current), Ponytail, High Ponytail, Single Braid, Twin Braids, Bob, Bun, Pixie, Side-swept, Wavy, Shaved Side, Curly.

**Pipeline:**
1. **Bald bases:** `Tools/hair.py` paints a bald base per body by replacing the hair with scalp and outline. Those bases are rebuilt through `walk_cycle.py`.
2. **Hair layer:** each hairstyle is drawn as an overlay per drawn direction (S, SW, W, NW, N). Every frame is built twice, with and without the hair, and the hair layer is the hair-class pixels of the "with" build.
3. **Atlas:** the tool packs all 256 hair frames (4 anims × 8 directions × 8 frames) into one atlas per hairstyle, with an offsets module.
4. **In game:** `SpriteCard` draws the hair as a second `ImageLabel` above the body, at each frame's offset. `Recolour` paints it with the hair ramp.
5. **Uploads:** one bald set per body (32 strips, replacing today's sheets), plus one atlas per hairstyle (24).

**Save:** the look string gains a hairstyle field: `m:sand:raven:undyed:messy`. Old 4-field strings still decode.

## 6. Creator flow

**Steps:** Look → Class → Origin → Traits → Begin. A step bar sits on top, and the live preview stays in the centre.

| Step | Left panel | Right panel |
| --- | --- | --- |
| Look | (as today) | Plus a hairstyle row once hairstyles land |
| Class | 6 classes | A card: role, weapon, armour, first power, Discipline, "switch at any shrine" |
| Origin | 5 origins | A small map of the Reach with the homelands marked, plus a card: start, standing, starting item |
| Traits | 16 traits | The two picks, upside in green and cost in red; "Begin" needs 2 |

**Reopening (C, until shrines and the Barber exist):** Look and Class only. Origin and traits are shown but locked.

## 7. Saving and checks (Appearance.server → Profile)

- **Storage:** the DataStore value becomes `{ v = 2, look = "...", class = "duelist", origin = "varrow", traits = { "a", "b" } }`. A plain string is the old look-only save.
- **Player attributes:** `Appearance`, `Class`, `Origin`, `Traits` ("a,b") and `AppearanceChosen`.
- **Server checks:**
  - every id must be known;
  - traits: exactly 2, different;
  - origin and traits are accepted only while `AppearanceChosen` is false;
  - class and look can change later.
- **Pure logic** (sanitising, encoding, rules) lives in `Shared/Profile.luau` with specs.

## 8. Build order

1. Data modules (Classes, Origins, Traits, Profile) with specs; server save and checks; origin spawn; creator steps.
2. Hairstyles: bald bases, the hair-layer pipeline and atlas, 24 styles drawn and audited, the `SpriteCard` hair layer and recolour, the export of uploads, and wiring after upload.
