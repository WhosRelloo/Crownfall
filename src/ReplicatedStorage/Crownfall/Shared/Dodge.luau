-- Dodge roll maths (blueprint 4.2, Art-Spec dodge): direction vectors, eased travel, i-frame window.
local Config = require(script.Parent.Config)

local Dodge = {}

local DIAGONAL = math.sqrt(0.5)
local VECTORS = { -- screen directions on the ground: the camera looks toward -Z, so south is +Z
	S = Vector3.new(0, 0, 1),
	N = Vector3.new(0, 0, -1),
	E = Vector3.new(1, 0, 0),
	W = Vector3.new(-1, 0, 0),
	SE = Vector3.new(DIAGONAL, 0, DIAGONAL),
	SW = Vector3.new(-DIAGONAL, 0, DIAGONAL),
	NE = Vector3.new(DIAGONAL, 0, -DIAGONAL),
	NW = Vector3.new(-DIAGONAL, 0, -DIAGONAL),
}

function Dodge.Vector(direction: string): Vector3
	return VECTORS[direction] or VECTORS.S
end

-- Studs travelled `elapsed` seconds into the roll: fast out, easing into the landing (1 - (1 - t)^2).
function Dodge.Travelled(elapsed: number): number
	local t = math.clamp(elapsed / Config.Movement.DodgeTime, 0, 1)
	return Config.Movement.DodgeDistance * (1 - (1 - t) ^ 2)
end

-- Studs per second at `elapsed` (the derivative of Travelled).
function Dodge.Speed(elapsed: number): number
	local t = math.clamp(elapsed / Config.Movement.DodgeTime, 0, 1)
	return Config.Movement.DodgeDistance * 2 * (1 - t) / Config.Movement.DodgeTime
end

function Dodge.Invulnerable(elapsed: number): boolean
	local w = Config.Movement.DodgeInvulnerable
	return elapsed >= w[1] and elapsed < w[2]
end

return Dodge
