-- Screen direction -> one of eight facings, each a 45-degree sector centred on its direction
-- (Docs/Art-Spec.md section 3). Screen y is up/away from the viewer.
local Facing = {}

local CLOCKWISE_FROM_N = { "N", "NE", "E", "SE", "S", "SW", "W", "NW" }

function Facing.FromScreen(dir: Vector2): string
	local angle = math.deg(math.atan2(dir.X, dir.Y)) -- 0 = N, 90 = E
	local index = math.floor(angle / 45 + 0.5) % 8
	return CLOCKWISE_FROM_N[index + 1]
end

return Facing
