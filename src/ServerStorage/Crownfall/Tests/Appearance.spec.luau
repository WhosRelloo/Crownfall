local RS = game:GetService("ReplicatedStorage")
local Appearance = require(RS.Crownfall.Shared.Appearance)
local ClassMap = require(RS.Crownfall.Render.ClassMap)
local T = require(script.Parent.TestKit)

local spec = {}

local RANGES = { [3] = { 43.2, 185.7 }, [4] = { 12.9, 59.3 }, [5] = { 14.1, 81.3 } }

spec["colour sets have the planned sizes, 5-stop ramps and one drawn entry each"] = function()
	T.eq(#Appearance.Options.skin, 8, "skin tones")
	T.eq(#Appearance.Options.hair, 12, "hair colours")
	T.eq(#Appearance.Options.outfit, 11, "undyed + 10 dyes")
	for _, slot in ipairs(Appearance.Slots) do
		local drawn, ids = 0, {}
		for _, entry in ipairs(Appearance.Options[slot]) do
			T.eq(#entry.Ramp, 5, slot .. " " .. entry.Id .. " ramp stops")
			T.falsy(ids[entry.Id], slot .. " ids are unique")
			ids[entry.Id] = true
			if entry.Original then
				drawn += 1
				T.eq(entry.Id, Appearance.Default[slot], "the drawn entry is the default")
			end
			-- dark to light
			local prev = -1
			for _, c in ipairs(entry.Ramp) do
				local lum = 0.3 * c.R + 0.59 * c.G + 0.11 * c.B
				T.truthy(lum > prev, slot .. " " .. entry.Id .. " ramp runs dark to light")
				prev = lum
			end
		end
		T.eq(drawn, 1, slot .. " has one drawn entry")
	end
end

spec["presets use real colours"] = function()
	T.eq(#Appearance.Presets, 8)
	for _, preset in ipairs(Appearance.Presets) do
		for _, slot in ipairs(Appearance.Slots) do
			T.truthy(Appearance.Find(slot, preset.Look[slot]), preset.Name .. " " .. slot)
		end
	end
end

spec["sanitize keeps valid picks and defaults the rest"] = function()
	local look = Appearance.Sanitize({ body = "f", skin = "deep", hair = "nope", outfit = 5 })
	T.eq(look.body, "f")
	T.eq(look.skin, "deep")
	T.eq(look.hair, Appearance.Default.hair)
	T.eq(look.outfit, Appearance.Default.outfit)
	T.eq(Appearance.Sanitize(nil).skin, Appearance.Default.skin)
	T.eq(Appearance.Sanitize({ body = "x" }).body, "m")
end

spec["encode and decode round-trip; junk decodes to the default"] = function()
	local look = { body = "m", skin = "umber", hair = "frost", outfit = "wine" }
	T.eq(Appearance.Encode(look), "m:umber:frost:wine:messy", "the body's own hairstyle by default")
	local back = Appearance.Decode("m:umber:frost:wine")
	for k, v in pairs(look) do
		T.eq(back[k], v, k)
	end
	T.eq(Appearance.Encode(Appearance.Decode(42)), Appearance.Encode(Appearance.Default))
	T.eq(Appearance.Encode(Appearance.Decode(string.rep("x", 200))), Appearance.Encode(Appearance.Default))
	T.eq(Appearance.Decode("m:deep").skin, "deep", "a short string keeps what it has")
	T.eq(Appearance.Decode("f:deep:ash:wine:bob").style, "bob")
	T.eq(Appearance.Decode("m:deep:ash:wine:bob").style, "messy", "a hairstyle from the other body falls back")
	T.eq(Appearance.Decode("f:deep:ash:wine").style, "long", "old saves get the body's own hair")
end

spec["random looks are valid; a slot dice changes only that slot"] = function()
	local rng = Random.new(7)
	for _ = 1, 50 do
		local look = Appearance.Random(rng)
		T.eq(Appearance.Encode(look), Appearance.Encode(Appearance.Sanitize(look)))
	end
	local base = { body = "m", skin = "deep", hair = "ash", outfit = "navy" }
	for _ = 1, 20 do
		local look = Appearance.Random(rng, base, "hair")
		T.eq(look.skin, "deep")
		T.eq(look.outfit, "navy")
	end
end

spec["the drawn look needs no painting"] = function()
	T.truthy(Appearance.IsDrawn(Appearance.Default))
	T.falsy(Appearance.IsDrawn({ body = "m", skin = "deep", hair = "raven", outfit = "undyed" }))
end

spec["recolour matches Tools/recolour.py"] = function()
	local ramps = Appearance.Ramps({ body = "m", skin = "deep", hair = "blonde", outfit = "navy" })
	local cases = { -- input, class, expected (from Tools/recolour.py)
		{ { 200, 136, 102 }, 3, { 117, 77, 57 } },
		{ { 156, 108, 83 }, 3, { 94, 57, 42 } },
		{ { 38, 25, 24 }, 4, { 161, 127, 71 } },
		{ { 55, 40, 37 }, 5, { 33, 42, 74 } },
		{ { 86, 45, 30 }, 5, { 84, 46, 33 } }, -- saturated leather strap: barely dyed
		{ { 62, 45, 34 }, 5, { 37, 48, 82 } },
	}
	for _, case in ipairs(cases) do
		local r, g, b = Appearance.RecolourPixel(case[1][1], case[1][2], case[1][3], case[2], ramps, RANGES)
		for i, v in ipairs({ r, g, b }) do
			T.truthy(math.abs(v - case[3][i]) <= 1, string.format("class %d channel %d: %d vs %d", case[2], i, v, case[3][i]))
		end
	end
end

spec["recolour leaves unpainted classes alone and spans the ramp"] = function()
	local ramps = Appearance.Ramps({ body = "m", skin = "porcelain", hair = "raven", outfit = "undyed" })
	local r, g, b = Appearance.RecolourPixel(10, 20, 30, 4, ramps, RANGES)
	T.eq(r * 65536 + g * 256 + b, 10 * 65536 + 20 * 256 + 30, "hair left as drawn")
	r, g, b = Appearance.RecolourPixel(0, 0, 0, 1, ramps, RANGES)
	T.eq(r + g + b, 0, "outline untouched")
	local ramp = Appearance.Find("skin", "porcelain").Ramp
	r = Appearance.RecolourPixel(255, 255, 255, 3, ramps, RANGES)
	T.eq(r, math.round(ramp[5].R * 255), "brightest skin -> lightest stop")
	r = Appearance.RecolourPixel(20, 10, 5, 3, ramps, RANGES)
	T.eq(r, math.round(ramp[1].R * 255), "darkest skin -> darkest stop")
end

spec["class maps (both bodies) decode to whole strips with known classes"] = function()
	T.eq(buffer.len(ClassMap.Decode("a3c2", 5, 1)), 5)
	local tiny = ClassMap.Decode("a3c2", 5, 1)
	T.eq(buffer.readu8(tiny, 2), 0)
	T.eq(buffer.readu8(tiny, 3), 2)
	for _, rig in ipairs({ "humanm", "humanf" }) do
	local maps = require(RS.Crownfall.Render.ClassMaps[rig])
	for anim, strips in pairs(maps.Anims) do
		local n = 0
		for direction, text in pairs(strips) do
			n += 1
			local buf = ClassMap.Decode(text, 768, 96)
			local painted = 0
			for i = 0, buffer.len(buf) - 1 do
				local k = buffer.readu8(buf, i)
				T.truthy(k <= 6, anim .. " " .. direction .. " class in range")
				if k >= 3 and k <= 5 then
					painted += 1
				end
			end
			T.truthy(painted > 2000, anim .. " " .. direction .. " has paintable pixels")
		end
		T.eq(n, 8, rig .. " " .. anim .. " has all 8 directions")
	end
	end
	T.truthy(require(RS.Crownfall.Render.ClassMaps.humanf).Anims.idle, "the female idle has stored maps")
end

return spec
