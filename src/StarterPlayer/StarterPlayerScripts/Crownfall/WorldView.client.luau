-- Draws every map in Shared/Maps on this client (Render/World): ground images, animated water, prop cards that
-- sway. Only visuals; the server builds the props' collision (World.server).
local RS = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Players = game:GetService("Players")
local Config = require(RS.Crownfall.Shared.Config)

local World = require(RS.Crownfall.Render.World)

local WATER_FPS = 4

local CANVAS = 4 -- SurfaceGui px per image px for props (crisp pixels)

local folder = Instance.new("Folder")
folder.Name = "CrownfallWorldView"
folder.Parent = workspace

local animated = {} -- { label, frames = { rects }, fps, phase }
local standing = {} -- tall props that can hide the player: { label, foot, w, h }
local FADE_TO = 0.65 -- a prop in front of the player turns this see-through
local SIN_PITCH = math.sin(math.rad(Config.Camera.Pitch))
local waters = {} -- { decal, frames = { ids } }

local function part(name: string, size: Vector3, cf: CFrame): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Transparency = 1
	p.Size = size
	p.CFrame = cf
	return p
end

local function image(parent: Instance, content: string, z: number?): ImageLabel
	local l = Instance.new("ImageLabel")
	l.BackgroundTransparency = 1
	l.Size = UDim2.fromScale(1, 1)
	l.ResampleMode = Enum.ResamplerMode.Pixelated
	l.Image = content
	l.ZIndex = z or 1
	l.Parent = parent
	return l
end

local function surface(p: Part, face: Enum.NormalId, canvas: Vector2): SurfaceGui
	local g = Instance.new("SurfaceGui")
	g.Face = face
	g.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	g.CanvasSize = canvas
	g.LightInfluence = 1
	g.Parent = p
	return g
end

local function build(map)
	local s, stretch = World.PixelStuds, World.Stretch
	local root = Instance.new("Folder")
	root.Name = map.Name
	-- ground: opaque tiles with the image as a decal, so it draws in the depth-tested pass and nothing standing on it
	-- can ever be drawn over (see-through ground was sorted against characters and could hide them). Water tiles
	-- carry 4 frames, ripples painted in, swapped in place.
	for _, c in ipairs(map.Chunks) do
		local w, d = map.Chunk * s, map.Chunk * s * stretch
		local centre = World.ToWorld(map, (c.cx + 0.5) * map.Chunk, (c.cz + 0.5) * map.Chunk) - Vector3.new(0, 0.5, 0)
		local p = Instance.new("Part")
		p.Name = "Ground"
		p.Anchored = true
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.CastShadow = false
		p.Material = Enum.Material.SmoothPlastic
		p.Color = Color3.fromRGB(46, 66, 36)
		-- a top-face decal lies upside down relative to the map (image x toward -X, y toward -Z): turned half round
		p.Size = Vector3.new(w, 1, d)
		p.CFrame = CFrame.new(centre) * CFrame.Angles(0, math.rad(180), 0)
		local decal = Instance.new("Decal")
		decal.Face = Enum.NormalId.Top
		decal.Texture = c.Frames[1]
		decal.Parent = p
		if #c.Frames > 1 then
			table.insert(waters, { decal = decal, frames = c.Frames })
		end
		p.Parent = root
	end
	-- props
	local atlases = map.Atlases
	for _, prop in ipairs(World.Props(map)) do
		local kind = map.Kinds[prop.kind]
		local first = kind.Frames[1]
		local w, h = first[4] * s, first[5] * s
		local foot = World.ToWorld(map, prop.x, prop.y)
		local p = part(prop.kind, Vector3.new(w, h, 0.05), World.CardCFrame(foot, h))
		local g = surface(p, Enum.NormalId.Front, Vector2.new(first[4], first[5]) * CANVAS)
		local l = image(g, atlases[first[1] + 1])
		l.ImageRectOffset, l.ImageRectSize = Vector2.new(first[2], first[3]), Vector2.new(first[4], first[5])
		if h > 2.5 then
			table.insert(standing, { label = l, foot = foot, w = w, h = h })
		end
		if #kind.Frames > 1 then
			table.insert(animated, { label = l, frames = kind.Frames, fps = kind.FPS, phase = (prop.x * 7 + prop.y * 3) % 97 / 97 })
		end
		p.Parent = root
	end
	root.Parent = folder
end

local maps = RS.Crownfall.Shared:FindFirstChild("Maps")
for _, module in ipairs(if maps then maps:GetChildren() else {}) do
	if module:IsA("ModuleScript") then
		build(require(module))
	end
end

-- animation: props sway at their own phase; water ripples flip frames
local last = 0
RunService.Heartbeat:Connect(function()
	local now = os.clock()
	if now - last < 1 / 12 then
		return
	end
	last = now
	for _, a in ipairs(animated) do
		local f = math.floor((now * a.fps + a.phase * #a.frames)) % #a.frames + 1
		local r = a.frames[f]
		a.label.ImageRectOffset = Vector2.new(r[2], r[3])
	end
	-- props standing between the camera and the player fade, so the player is never hidden
	local root = Players.LocalPlayer.Character and Players.LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
	if root then
		local me = root.Position
		for _, s in ipairs(standing) do
			local dz = s.foot.Z - me.Z -- > 0: the prop stands nearer the camera than the player
			local covers = dz > 0 and dz * SIN_PITCH < s.h - 0.5 and math.abs(s.foot.X - me.X) < s.w / 2 + 0.6
			local want = if covers then FADE_TO else 0
			if s.label.ImageTransparency ~= want then
				s.label.ImageTransparency += math.clamp(want - s.label.ImageTransparency, -0.15, 0.15)
			end
		end
	end
	local wf = math.floor(now * WATER_FPS)
	for _, w in ipairs(waters) do
		w.decal.Texture = w.frames[wf % #w.frames + 1]
	end
end)
