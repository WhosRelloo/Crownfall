-- 2D pixel-art maps in the 2.5D view (Tools/world/*.py, Shared/Maps/*): the ground lies flat as images, stretched
-- along the camera's depth by 1 / sin(pitch) so its pixels come out square on screen at the characters' scale; props
-- stand on their foot pixel as cards facing the (fixed) camera, like the characters do.
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local CameraMath = require(script.Parent.CameraMath)

local World = {}

World.PixelStuds = 5 / 64 -- one character pixel, in studs (across)
World.Stretch = 1 / math.sin(math.rad(Config.Camera.Pitch)) -- ground depth stretch
World.GroundY = 0.05 -- the ground images' top, just over the baseplate

-- The direction the camera looks (never changes: the camera only follows, it doesn't turn).
World.Look = -CameraMath.Offset(Config.Camera.Pitch, Config.Camera.Distance).Unit

-- Map pixel -> world position on the ground.
function World.ToWorld(map, x: number, y: number): Vector3
	local s = World.PixelStuds
	return Vector3.new((x - map.Size.X / 2) * s, World.GroundY, (y - map.Size.Y / 2) * s * World.Stretch)
end

-- The props as a list of { kind, x, y } from the packed "k,x,y;..." string.
function World.Props(map)
	local list = {}
	for k, x, y in string.gmatch(map.Props, "(%d+),(%d+),(%d+)") do
		table.insert(list, { kind = map.KindOrder[tonumber(k) :: number], x = tonumber(x), y = tonumber(y) })
	end
	return list
end

-- A card standing on `foot`, w x h studs, facing the camera.
function World.CardCFrame(foot: Vector3, height: number): CFrame
	local cf = CFrame.lookAt(foot, foot - World.Look)
	return cf + cf.UpVector * (height / 2)
end

return World
