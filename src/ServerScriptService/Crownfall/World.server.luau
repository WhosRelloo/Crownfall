-- Collision for map props (Shared/Maps): an invisible pillar at the foot of each prop that blocks walking (trees,
-- rocks, stumps, big mushrooms). The look is drawn per client by WorldView.client.
local RS = game:GetService("ReplicatedStorage")

local World = require(RS.Crownfall.Render.World)

local PILLAR_HEIGHT = 6

local folder = Instance.new("Folder")
folder.Name = "CrownfallWorld"
folder.Parent = workspace

local maps = RS.Crownfall.Shared:FindFirstChild("Maps")
for _, module in ipairs(if maps then maps:GetChildren() else {}) do
	if not module:IsA("ModuleScript") then
		continue
	end
	local map = require(module)
	local root = Instance.new("Folder")
	root.Name = map.Name
	for _, prop in ipairs(World.Props(map)) do
		local kind = map.Kinds[prop.kind]
		if kind.Block > 0 then
			local r = kind.Block * World.PixelStuds
			local p = Instance.new("Part")
			p.Name = prop.kind
			p.Shape = Enum.PartType.Cylinder
			p.Anchored = true
			p.Transparency = 1
			p.CastShadow = false
			p.Size = Vector3.new(PILLAR_HEIGHT, r * 2, r * 2)
			local foot = World.ToWorld(map, prop.x, prop.y)
			-- the pillar sits a little behind the foot (a trunk's base is where the shadow is)
			p.CFrame = CFrame.new(foot + Vector3.new(0, PILLAR_HEIGHT / 2, -r * 0.5)) * CFrame.Angles(0, 0, math.rad(90))
			p.Parent = root
		end
	end
	root.Parent = folder
end
