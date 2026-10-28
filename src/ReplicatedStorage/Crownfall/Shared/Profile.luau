-- A character's creation choices: look (Shared/Appearance), class, origin and traits
-- (Docs/Plans/2026-10-28-class-origin-traits-hair.md, section 7). Pure logic, shared by the server's checks,
-- the creator and the specs.
local Appearance = require(script.Parent.Appearance)
local Classes = require(script.Parent.Classes)
local Origins = require(script.Parent.Origins)
local Traits = require(script.Parent.Traits)

local Profile = {}

export type Profile = { look: string, class: string, origin: string, traits: { string } }

function Profile.Default(): Profile
	return {
		look = Appearance.Encode(Appearance.Default),
		class = Classes.Default,
		origin = Origins.Default,
		traits = {},
	}
end

-- Exactly Traits.Pick different, known traits.
function Profile.ValidTraits(list: any): boolean
	if type(list) ~= "table" or #list ~= Traits.Pick then
		return false
	end
	local seen = {}
	for _, id in ipairs(list) do
		if not Traits.Find(id) or seen[id] then
			return false
		end
		seen[id] = true
	end
	return true
end

-- Any value (a v2 table, an old look-only string, junk) -> a valid profile. Invalid trait picks become none.
function Profile.Sanitize(value: any): Profile
	local out = Profile.Default()
	if type(value) == "string" then -- saves from before classes: just the look
		out.look = Appearance.Encode(Appearance.Decode(value))
		return out
	end
	if type(value) ~= "table" then
		return out
	end
	out.look = Appearance.Encode(Appearance.Decode(value.look))
	if Classes.Find(value.class) then
		out.class = value.class
	end
	if Origins.Find(value.origin) then
		out.origin = value.origin
	end
	if Profile.ValidTraits(value.traits) then
		out.traits = table.clone(value.traits)
	end
	return out
end

-- What the DataStore keeps.
function Profile.ToSave(profile: Profile)
	return { v = 2, look = profile.look, class = profile.class, origin = profile.origin, traits = table.clone(profile.traits) }
end

-- Traits travel as one attribute: "light_footed,hawk_eyed".
function Profile.EncodeTraits(list: { string }): string
	return table.concat(list, ",")
end

function Profile.DecodeTraits(text: any): { string }
	if type(text) ~= "string" or text == "" or #text > 80 then
		return {}
	end
	local list = string.split(text, ",")
	return if Profile.ValidTraits(list) then list else {}
end

-- A change the player asks for after creation: look and class may change (class at a shrine); origin and traits
-- are fixed once chosen. Returns the profile to keep.
function Profile.Apply(current: Profile, request: any, firstTime: boolean): Profile
	local want = Profile.Sanitize(request)
	local out = table.clone(current)
	out.look = want.look
	if type(request) == "table" and Classes.Find(request.class) then
		out.class = request.class
	end
	if firstTime then
		if type(request) == "table" and Origins.Find(request.origin) then
			out.origin = request.origin
		end
		if type(request) == "table" and Profile.ValidTraits(request.traits) then
			out.traits = table.clone(request.traits)
		end
	end
	return out
end

return Profile
