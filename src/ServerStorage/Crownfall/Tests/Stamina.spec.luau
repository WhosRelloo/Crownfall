local RS = game:GetService("ReplicatedStorage")
local Stamina = require(RS.Crownfall.Shared.Stamina)
local T = require(script.Parent.TestKit)

local spec = {}

spec["starts full"] = function()
	T.eq(Stamina.new(100).value, 100)
end

spec["spend subtracts the cost"] = function()
	local s = Stamina.new(100)
	T.truthy(s:Spend(25, 0))
	T.eq(s.value, 75)
end

spec["overdraw empties and exhausts for 1 s"] = function()
	local s = Stamina.new(100)
	s.value = 10
	T.truthy(s:Spend(25, 5), "the last action may overdraw")
	T.eq(s.value, 0)
	T.truthy(s:IsExhausted(5.5))
	T.falsy(s:IsExhausted(6.0))
	T.falsy(s:Spend(8, 5.5), "refused while exhausted")
end

spec["no regen before the 0.6 s delay"] = function()
	local s = Stamina.new(100)
	s:Spend(50, 0)
	s:Update(0.5, 0.5)
	T.eq(s.value, 50)
end

spec["regen after the delay, capped at max"] = function()
	local s = Stamina.new(100)
	s:Spend(50, 0)
	s:Update(0.6, 1.0)
	T.eq(s.value, 90)
	s:Update(2, 1)
	T.eq(s.value, 100)
end

spec["empty to full in about 2.5 s after the delay"] = function()
	local s = Stamina.new(100)
	s.value = 1
	s:Spend(25, 0)
	local t = 0.6
	for _ = 1, 25 do
		s:Update(t, 0.1)
		t += 0.1
	end
	T.near(s.value, 100, 1e-6)
end

spec["drain spends per second"] = function()
	local s = Stamina.new(100)
	T.truthy(s:Drain(12, 0.5, 0))
	T.eq(s.value, 94)
end

return spec
