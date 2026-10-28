local RS = game:GetService("ReplicatedStorage")
local Dodge = require(RS.Crownfall.Shared.Dodge)
local Config = require(RS.Crownfall.Shared.Config)
local T = require(script.Parent.TestKit)

local spec = {}

spec["direction names map to world vectors on the ground"] = function()
	T.eq(Dodge.Vector("S"), Vector3.new(0, 0, 1), "south is toward the camera (+Z)")
	T.eq(Dodge.Vector("N"), Vector3.new(0, 0, -1))
	T.eq(Dodge.Vector("E"), Vector3.new(1, 0, 0))
	T.eq(Dodge.Vector("W"), Vector3.new(-1, 0, 0))
	local sw = Dodge.Vector("SW")
	T.near(sw.Magnitude, 1)
	T.near(sw.X, -math.sqrt(0.5))
	T.near(sw.Z, math.sqrt(0.5))
end

spec["travel eases out and covers the full distance"] = function()
	local d, t = Config.Movement.DodgeDistance, Config.Movement.DodgeTime
	T.near(Dodge.Travelled(0), 0)
	T.near(Dodge.Travelled(t), d)
	T.near(Dodge.Travelled(t * 2), d, 1e-6, "stays at the end")
	T.truthy(Dodge.Travelled(t / 2) > d / 2, "more than half the way at half time (fast out)")
end

spec["speed is highest at the start and zero at the end"] = function()
	local t = Config.Movement.DodgeTime
	T.truthy(Dodge.Speed(0) > Dodge.Speed(t / 2))
	T.near(Dodge.Speed(t), 0)
end

spec["invulnerable only on frames 2 to 5"] = function()
	local frame = 1 / 20
	T.falsy(Dodge.Invulnerable(frame * 0.5), "frame 1")
	T.truthy(Dodge.Invulnerable(frame * 1.5), "frame 2")
	T.truthy(Dodge.Invulnerable(frame * 4.5), "frame 5")
	T.falsy(Dodge.Invulnerable(frame * 5.5), "frame 6")
end

return spec
