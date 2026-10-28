-- Character appearance (Docs/Character-Customization.md, Phase A): what a player picked, how it is saved and
-- checked, and the recolour maths. Colour sets live in AppearanceData (generated from Art/Sprites/palettes.json).
local Data = require(script.Parent.AppearanceData)

local Appearance = {}

-- Colour classes in the class maps (Tools/colour_classes.py). Only Skin, Hair and Outfit are recoloured.
Appearance.Class = { Outline = 1, Steel = 2, Skin = 3, Hair = 4, Outfit = 5, Boots = 6 }
local SLOT_CLASS = { skin = 3, hair = 4, outfit = 5 }

Appearance.Slots = { "skin", "hair", "outfit" }
Appearance.Options = Data

-- Bodies: Art names the art manifest (Render/Art). A body whose art isn't in yet falls back to the first.
Appearance.Bodies = {
	{ Id = "m", Name = "Male", Art = "humanm" },
	{ Id = "f", Name = "Female", Art = "humanf" },
}

export type Look = { body: string, skin: string, hair: string, outfit: string }

Appearance.Default = { body = "m", skin = "sand", hair = "raven", outfit = "undyed" } :: Look

-- Artist-picked starting looks; the creator starts from one and the player edits from there.
Appearance.Presets = {
	{ Name = "Wanderer", Look = { skin = "sand", hair = "raven", outfit = "undyed" } },
	{ Name = "Northman", Look = { skin = "porcelain", hair = "blonde", outfit = "navy" } },
	{ Name = "Ashborn", Look = { skin = "deep", hair = "white", outfit = "wine" } },
	{ Name = "Fox", Look = { skin = "tan", hair = "copper", outfit = "linen" } },
	{ Name = "Greywarden", Look = { skin = "bronze", hair = "ash", outfit = "moss" } },
	{ Name = "Cutpurse", Look = { skin = "umber", hair = "auburn", outfit = "charcoal" } },
	{ Name = "Frostmarked", Look = { skin = "fair", hair = "frost", outfit = "slate" } },
	{ Name = "Cinder", Look = { skin = "olive", hair = "ember", outfit = "ochre" } },
}

local DYE_FULL, DYE_NONE = 0.50, 0.66 -- outfit saturation: fully dyed up to DYE_FULL, untouched from DYE_NONE (leather)

function Appearance.Find(slot: string, id: string?)
	for _, entry in ipairs(Data[slot] or {}) do
		if entry.Id == id then
			return entry
		end
	end
	return nil
end

local function findBody(id: string?)
	for _, body in ipairs(Appearance.Bodies) do
		if body.Id == id then
			return body
		end
	end
	return nil
end
Appearance.FindBody = findBody

-- Any table (or nil) -> a valid look: unknown or missing fields take the default.
function Appearance.Sanitize(look: any): Look
	local out = table.clone(Appearance.Default)
	if type(look) ~= "table" then
		return out
	end
	if type(look.body) == "string" and findBody(look.body) then
		out.body = look.body
	end
	for _, slot in ipairs(Appearance.Slots) do
		local id = look[slot]
		if type(id) == "string" and Appearance.Find(slot, id) then
			out[slot] = id
		end
	end
	return out
end

-- Saved and replicated as one short string: "m:sand:raven:undyed".
function Appearance.Encode(look: Look): string
	look = Appearance.Sanitize(look)
	return table.concat({ look.body, look.skin, look.hair, look.outfit }, ":")
end

function Appearance.Decode(text: any): Look
	if type(text) ~= "string" or #text > 80 then
		return Appearance.Sanitize(nil)
	end
	local parts = string.split(text, ":")
	return Appearance.Sanitize({ body = parts[1], skin = parts[2], hair = parts[3], outfit = parts[4] })
end

-- A random look; with `slot`, only that slot changes (the creator's per-row dice).
function Appearance.Random(rng: Random, base: Look?, slot: string?): Look
	local out = Appearance.Sanitize(base)
	for _, s in ipairs(Appearance.Slots) do
		if slot == nil or slot == s then
			local list = Data[s]
			out[s] = list[rng:NextInteger(1, #list)].Id
		end
	end
	return out
end

-- Ramps to paint with, by class id; slots left as drawn ("Original" entries) are absent.
function Appearance.Ramps(look: Look): { [number]: { Color3 } }
	local ramps = {}
	for _, slot in ipairs(Appearance.Slots) do
		local entry = Appearance.Find(slot, look[slot])
		if entry and not entry.Original then
			ramps[SLOT_CLASS[slot]] = entry.Ramp
		end
	end
	return ramps
end

-- True when nothing needs repainting (every slot is as drawn).
function Appearance.IsDrawn(look: Look): boolean
	return next(Appearance.Ramps(look)) == nil
end

-- ranges: { skin = {lo, hi}, hair = {lo, hi}, outfit = {lo, hi} } from the art's class maps; by class id here.
function Appearance.RangesByClass(ranges)
	return { [3] = ranges.skin, [4] = ranges.hair, [5] = ranges.outfit }
end

local function rampAt(ramp: { Color3 }, t: number): (number, number, number)
	local f = math.clamp(t, 0, 1) * (#ramp - 1)
	local i = math.min(math.floor(f), #ramp - 2)
	local u = f - i
	local a, b = ramp[i + 1], ramp[i + 2]
	return a.R + (b.R - a.R) * u, a.G + (b.G - a.G) * u, a.B + (b.B - a.B) * u
end

-- One pixel (0-255 channels): its brightness, placed in its class's range, picks a point on the ramp.
-- Outfit dye fades out on saturated pixels so leather straps, belts and bracers keep their colour.
-- Must match Tools/recolour.py.
function Appearance.RecolourPixel(r: number, g: number, b: number, class: number, ramps, ranges): (number, number, number)
	local ramp = ramps[class]
	if not ramp then
		return r, g, b
	end
	local range = ranges[class]
	local lum = 0.3 * r + 0.59 * g + 0.11 * b
	local nr, ng, nb = rampAt(ramp, (lum - range[1]) / (range[2] - range[1]))
	nr, ng, nb = math.round(nr * 255), math.round(ng * 255), math.round(nb * 255)
	if class == 5 then
		local hi, lo = math.max(r, g, b), math.min(r, g, b)
		local s = if hi > 0 then (hi - lo) / hi else 0
		local w = math.clamp((DYE_NONE - s) / (DYE_NONE - DYE_FULL), 0, 1)
		nr, ng, nb = math.round(r + (nr - r) * w), math.round(g + (ng - g) * w), math.round(b + (nb - b) * w)
	end
	return nr, ng, nb
end

return Appearance
