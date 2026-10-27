-- Geometry for the fixed three-quarter camera. Camera yaw is fixed at 0 in M1: the camera sits on +Z
-- looking toward -Z, so screen-right is +X and screen-up (away from the viewer) is -Z.
local CameraMath = {}

function CameraMath.Offset(pitchDeg: number, distance: number): Vector3
	local p = math.rad(pitchDeg)
	return Vector3.new(0, math.sin(p) * distance, math.cos(p) * distance)
end

function CameraMath.ToScreen(v: Vector3): Vector2
	return Vector2.new(v.X, -v.Z)
end

return CameraMath
