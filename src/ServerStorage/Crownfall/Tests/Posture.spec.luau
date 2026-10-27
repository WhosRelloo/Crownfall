local RS = game:GetService("ReplicatedStorage")
local Posture = require(RS.Crownfall.Shared.Posture)
local T = require(script.Parent.TestKit)

local spec = {}

spec["reaching max breaks posture once"] = function()
	local p = Posture.new(100, "Enemy")
	T.falsy(p:Add(60, 0))
	T.truthy(p:Add(60, 0.1), "this hit breaks")
	T.truthy(p:IsBroken(0.2))
	T.falsy(p:Add(10, 0.3), "hits while broken do nothing")
end

spec["enemy break lasts 1.5 s, then posture resets to 0"] = function()
	local p = Posture.new(100, "Enemy")
	p:Add(100, 0)
	p:Update(1.4, 0.1, 1)
	T.truthy(p:IsBroken(1.4))
	T.eq(p.value, 100)
	p:Update(1.5, 0.1, 1)
	T.falsy(p:IsBroken(1.5))
	T.eq(p.value, 0)
end

spec["player break lasts 0.9 s"] = function()
	local p = Posture.new(100, "Player")
	p:Add(100, 0)
	T.truthy(p:IsBroken(0.89))
	T.falsy(p:IsBroken(0.9))
end

spec["no decay within 1.5 s of the last hit"] = function()
	local p = Posture.new(100, "Enemy")
	p:Add(50, 0)
	p:Update(1.4, 1, 1)
	T.eq(p.value, 50)
end

spec["decay is 30/s at full health and 10/s at zero health"] = function()
	local full = Posture.new(100, "Enemy")
	full:Add(50, 0)
	full:Update(1.5, 1, 1)
	T.near(full.value, 20)
	local low = Posture.new(100, "Enemy")
	low:Add(50, 0)
	low:Update(1.5, 1, 0)
	T.near(low.value, 40)
end

spec["co-op scale shrinks with each extra attacker"] = function()
	T.eq(Posture.CoopScale(1), 1)
	T.near(Posture.CoopScale(2), 0.6)
	T.near(Posture.CoopScale(3), 0.36)
end

spec["unknown kind is rejected"] = function()
	T.falsy(pcall(Posture.new, 100, "Dragon"))
end

return spec
