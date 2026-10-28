local RS = game:GetService("ReplicatedStorage")
local Shared = RS.Crownfall.Shared
local Classes = require(Shared.Classes)
local Origins = require(Shared.Origins)
local Traits = require(Shared.Traits)
local Profile = require(Shared.Profile)
local T = require(script.Parent.TestKit)

local spec = {}

spec["6 classes and 5 origins with unique ids and full cards"] = function()
	T.eq(#Classes.List, 6)
	T.eq(#Origins.List, 5)
	for _, list in ipairs({ Classes.List, Origins.List }) do
		local seen = {}
		for _, entry in ipairs(list) do
			T.falsy(seen[entry.Id], "unique id " .. entry.Id)
			seen[entry.Id] = true
		end
	end
	for _, c in ipairs(Classes.List) do
		for _, field in ipairs({ "Name", "Weapon", "Armour", "Power", "Discipline", "Role" }) do
			T.truthy(type(c[field]) == "string" and #c[field] > 0, c.Id .. " " .. field)
		end
	end
	for _, o in ipairs(Origins.List) do
		T.truthy(o.Map.X >= 0 and o.Map.X <= 1 and o.Map.Y >= 0 and o.Map.Y <= 1, o.Id .. " on the map")
		T.truthy(typeof(o.Spawn) == "Vector3", o.Id .. " default spawn")
		T.truthy(o.Standing.Up, o.Id .. " standing")
	end
	T.truthy(Classes.Find(Classes.Default))
	T.truthy(Origins.Find(Origins.Default))
end

spec["16 traits, each one real upside and one real cost, none over 25%"] = function()
	T.eq(#Traits.List, 16)
	local seen = {}
	for _, trait in ipairs(Traits.List) do
		T.falsy(seen[trait.Id], "unique " .. trait.Id)
		seen[trait.Id] = true
		T.truthy(trait.Up[1] ~= trait.Down[1], trait.Id .. " up and down touch different stats")
		for _, side in ipairs({ "Up", "Down" }) do
			local stat, value, text = trait[side][1], trait[side][2], trait[side][3]
			local info = Traits.Stats[stat]
			T.truthy(info, trait.Id .. " " .. side .. " stat " .. tostring(stat))
			T.truthy(type(text) == "string" and #text > 0, trait.Id .. " " .. side .. " text")
			local better = Traits.IsBetter(stat, value)
			T.eq(better, side == "Up", trait.Id .. " " .. side .. " goes the right way")
			local change = math.abs(value - info.Base) / info.Base
			T.truthy(change > 0 and change <= 0.25 + 1e-9, string.format("%s %s changes %.0f%%", trait.Id, side, change * 100))
		end
	end
end

spec["trait values read through one lookup and stack"] = function()
	T.eq(Traits.Value("DodgeCost", {}), 25)
	T.eq(Traits.Value("DodgeCost", { "light_footed" }), 22)
	T.eq(Traits.Value("DodgeCost", { "light_footed", "iron_grip" }), 25, "-3 and +3 cancel")
	T.near(Traits.Value("BlockPostureTaken", { "light_footed", "iron_grip" }), 0.95, 1e-9)
	T.eq(Traits.Value("MaxStamina", { "deep_lungs", "hawk_eyed" }), 110)
	T.eq(Traits.Value("MaxStamina", { "nope" }), 100, "unknown ids ignored")
end

spec["traits must be exactly 2 different known ones"] = function()
	T.truthy(Profile.ValidTraits({ "fleet", "tinker" }))
	T.falsy(Profile.ValidTraits({ "fleet" }))
	T.falsy(Profile.ValidTraits({ "fleet", "fleet" }))
	T.falsy(Profile.ValidTraits({ "fleet", "tinker", "hardy" }))
	T.falsy(Profile.ValidTraits({ "fleet", "made_up" }))
	T.falsy(Profile.ValidTraits("fleet,tinker"))
	T.eq(#Profile.DecodeTraits("fleet,tinker"), 2)
	T.eq(#Profile.DecodeTraits("fleet,fleet"), 0)
	T.eq(Profile.EncodeTraits({ "fleet", "tinker" }), "fleet,tinker")
end

spec["profiles sanitise; old look-only saves still load"] = function()
	local old = Profile.Sanitize("f:deep:ash:wine")
	T.eq(old.look, "f:deep:ash:wine:long")
	T.eq(old.class, Classes.Default)
	T.eq(#old.traits, 0)
	local p = Profile.Sanitize({ v = 2, look = "m:tan:copper:linen", class = "warder", origin = "lantern", traits = { "hardy", "fleet" } })
	T.eq(p.class, "warder")
	T.eq(p.origin, "lantern")
	T.eq(Profile.EncodeTraits(p.traits), "hardy,fleet")
	local junk = Profile.Sanitize({ class = "king", origin = 3, traits = { "x", "y" } })
	T.eq(junk.class, Classes.Default)
	T.eq(junk.origin, Origins.Default)
	T.eq(#junk.traits, 0)
	local saved = Profile.ToSave(p)
	T.eq(saved.v, 2)
	T.eq(Profile.Sanitize(saved).origin, "lantern")
end

spec["after creation only look and class can change"] = function()
	local current = Profile.Sanitize({ look = "m:tan:copper:linen", class = "duelist", origin = "varrow", traits = { "fleet", "tinker" } })
	local ask = { look = "m:deep:ash:wine", class = "breaker", origin = "compact", traits = { "hardy", "haggler" } }
	local later = Profile.Apply(current, ask, false)
	T.eq(later.look, "m:deep:ash:wine:messy")
	T.eq(later.class, "breaker")
	T.eq(later.origin, "varrow", "origin fixed")
	T.eq(Profile.EncodeTraits(later.traits), "fleet,tinker", "traits fixed")
	local first = Profile.Apply(Profile.Default(), ask, true)
	T.eq(first.origin, "compact")
	T.eq(Profile.EncodeTraits(first.traits), "hardy,haggler")
	local bad = Profile.Apply(Profile.Default(), { class = "king", traits = { "fleet" } }, true)
	T.eq(bad.class, Classes.Default)
	T.eq(#bad.traits, 0)
end

return spec
