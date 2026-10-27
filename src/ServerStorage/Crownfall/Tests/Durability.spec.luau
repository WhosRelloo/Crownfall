local RS = game:GetService("ReplicatedStorage")
local Durability = require(RS.Crownfall.Shared.Durability)
local T = require(script.Parent.TestKit)

local spec = {}

spec["wear amounts follow the kind"] = function()
	local d = Durability.new(100)
	d:Wear("Hit")
	d:Wear("Block")
	d:Wear("GuardBroken")
	T.eq(d.value, 89)
	d:Wear("PerfectParry")
	T.near(d.value, 88.9)
end

spec["states by fraction"] = function()
	T.eq(Durability.new(100, 26):State(), "Ok")
	T.eq(Durability.new(100, 25):State(), "Warn")
	T.eq(Durability.new(100, 10):State(), "Critical")
	T.eq(Durability.new(100, 0):State(), "Dulled")
end

spec["never goes below zero and never breaks"] = function()
	local d = Durability.new(100, 3)
	d:Wear("GuardBroken")
	T.eq(d.value, 0)
	T.eq(d:State(), "Dulled")
end

spec["dulled weapons deal 60% damage"] = function()
	T.eq(Durability.new(100, 1):DamageMultiplier(), 1)
	T.near(Durability.new(100, 0):DamageMultiplier(), 0.6)
end

spec["whetstone restores 30%, smith restores fully"] = function()
	local d = Durability.new(100, 10)
	d:Repair(0.3)
	T.eq(d.value, 40)
	d:Repair(0.9)
	T.eq(d.value, 100, "capped at max")
	d.value = 5
	d:Repair()
	T.eq(d.value, 100)
end

spec["unknown wear kind is rejected"] = function()
	local d = Durability.new(100)
	T.falsy(pcall(d.Wear, d, "Lava"))
end

return spec
