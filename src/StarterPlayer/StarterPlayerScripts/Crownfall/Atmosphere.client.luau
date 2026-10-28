-- Mirefen's air: fireflies drifting and blinking over the wet ground near the player, and a thin swamp haze sliding
-- slowly across the screen. Only visuals, client side. Fireflies gather where the map's waterside props are (reeds,
-- mushrooms, lily pads), within reach of the player; the haze is a screen layer, so it never sorts against the world.
local RS = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Players = game:GetService("Players")

local World = require(RS.Crownfall.Render.World)

local HAZE = "rbxassetid://75180384536864"
local HAZE_ALPHA = 0.84 -- image transparency of the haze layers (1 = invisible)
local FLIES = 36
local NEAR = 30 -- studs: fireflies live within this distance of the player
local PIXEL = 5 / 64 -- one map pixel, studs

local player = Players.LocalPlayer

-- where fireflies like to be: every waterside prop on every map
local spots = {}
local maps = RS.Crownfall.Shared:FindFirstChild("Maps")
for _, module in ipairs(if maps then maps:GetChildren() else {}) do
	if module:IsA("ModuleScript") then
		local map = require(module)
		for _, prop in ipairs(World.Props(map)) do
			local k = prop.kind
			if k:find("^reeds") or k:find("^mushroom") or k:find("^lily") then
				table.insert(spots, World.ToWorld(map, prop.x, prop.y))
			end
		end
	end
end

-- fireflies: a bright 1-pixel core in a soft 3-pixel glow, on billboards
local anchor = Instance.new("Part")
anchor.Name = "CrownfallFireflies"
anchor.Anchored = true
anchor.CanCollide = false
anchor.CanQuery = false
anchor.CanTouch = false
anchor.Transparency = 1
anchor.Size = Vector3.one
anchor.Parent = workspace

local function newFly()
	local att = Instance.new("Attachment")
	att.Parent = anchor
	local g = Instance.new("BillboardGui")
	g.Adornee = att
	g.Size = UDim2.fromScale(PIXEL * 7, PIXEL * 7)
	g.LightInfluence = 0
	g.Parent = att
	local halo = Instance.new("Frame")
	halo.AnchorPoint = Vector2.new(0.5, 0.5)
	halo.Position = UDim2.fromScale(0.5, 0.5)
	halo.Size = UDim2.fromScale(0.72, 0.72)
	halo.BorderSizePixel = 0
	halo.BackgroundColor3 = Color3.fromRGB(200, 255, 140)
	halo.Parent = g
	local core = Instance.new("Frame")
	core.AnchorPoint = Vector2.new(0.5, 0.5)
	core.Position = UDim2.fromScale(0.5, 0.5)
	core.Size = UDim2.fromScale(0.29, 0.29)
	core.BorderSizePixel = 0
	core.BackgroundColor3 = Color3.fromRGB(250, 255, 210)
	core.Parent = g
	return { att = att, halo = halo, core = core, home = nil, seed = math.random() * 100, life = 0 }
end

local flies = {}
for i = 1, FLIES do
	flies[i] = newFly()
end

local function rehome(f, me: Vector3)
	local near = {}
	for _, s in ipairs(spots) do
		if (s - me).Magnitude < NEAR then
			table.insert(near, s)
		end
	end
	local base = if #near > 0 then near[math.random(#near)] else nil
	if base then
		f.home = base + Vector3.new((math.random() - 0.5) * 6, 0.6 + math.random() * 2.2, (math.random() - 0.5) * 6)
	else
		f.home = nil
	end
	f.life = 6 + math.random() * 10
end

-- haze: two wide layers drifting at different speeds, wrapping
local gui = Instance.new("ScreenGui")
gui.Name = "CrownfallAtmosphere"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = -10 -- under every UI panel
gui.Parent = player:WaitForChild("PlayerGui")

local layers = {}
for i, spec in ipairs({ { speed = 0.006, y = 0.55, h = 0.9 }, { speed = -0.004, y = 0.25, h = 0.7 } }) do
	local strip = Instance.new("Frame")
	strip.BackgroundTransparency = 1
	strip.Size = UDim2.fromScale(2, spec.h)
	strip.Position = UDim2.fromScale(0, spec.y - spec.h / 2)
	strip.Parent = gui
	for k = 0, 1 do
		local l = Instance.new("ImageLabel")
		l.BackgroundTransparency = 1
		l.Image = HAZE
		l.ImageTransparency = HAZE_ALPHA + (i - 1) * 0.06
		l.ImageColor3 = Color3.fromRGB(196, 214, 190)
		l.Size = UDim2.fromScale(0.5, 1)
		l.Position = UDim2.fromScale(k * 0.5, 0)
		l.Parent = strip
	end
	layers[i] = { strip = strip, speed = spec.speed, x = math.random() }
end

local last = 0
RunService.Heartbeat:Connect(function(dt)
	local now = os.clock()
	for _, l in ipairs(layers) do
		l.x = (l.x + l.speed * dt) % 1
		l.strip.Position = UDim2.new(-l.x, 0, l.strip.Position.Y.Scale, 0)
	end
	if now - last < 1 / 24 then
		return
	end
	local step = now - last
	last = now
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	if not root then
		return
	end
	local me = root.Position
	for _, f in ipairs(flies) do
		f.life -= step
		if f.life <= 0 or not f.home or (f.home - me).Magnitude > NEAR + 6 then
			rehome(f, me)
		end
		if f.home then
			local t = now * 0.6 + f.seed
			f.att.WorldPosition = f.home
				+ Vector3.new(math.sin(t * 1.3) * 1.4, math.sin(t * 2.1) * 0.5, math.cos(t * 0.9) * 1.1)
			-- blink: slow pulse with a short dark gap, fading in and out at the ends of its life
			local pulse = math.clamp(math.sin(t * 2.4) * 1.4 + 0.4, 0, 1)
			local fade = math.clamp(math.min(f.life, 1.5) / 1.5, 0, 1)
			local on = pulse * fade
			f.core.BackgroundTransparency = 1 - on
			f.halo.BackgroundTransparency = 1 - on * 0.5
		else
			f.core.BackgroundTransparency = 1
			f.halo.BackgroundTransparency = 1
		end
	end
end)
