-- Hides every character's Roblox body on this client and draws a 2.5D sprite card in its place.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local Appearance = require(RS.Crownfall.Shared.Appearance)
local Render = RS.Crownfall.Render
local SpriteCard = require(Render.SpriteCard)
local SheetMath = require(Render.SheetMath)
local Facing = require(Render.Facing)
local CameraMath = require(Render.CameraMath)

local Arts = require(Render.Arts)
local art = Arts.Default
local artFor = Arts.For

-- Load every animation image up front, so switching to an animation (walk -> run) never shows a
-- blank frame while its image downloads.
task.spawn(function()
	local ids = {}
	for _, outfit in pairs((art.Layers and art.Layers.full) or {}) do
		for _, id in pairs(outfit) do
			table.insert(ids, id)
		end
	end
	for _, def in pairs(art.Anims) do
		for _, id in pairs(def.Images or {}) do
			table.insert(ids, id)
		end
	end
	if #ids > 0 then
		game:GetService("ContentProvider"):PreloadAsync(ids)
	end
end)

local camera = workspace.CurrentCamera
local folder = Instance.new("Folder")
folder.Name = "CrownfallSprites"
folder.Parent = workspace

local tracked = {} -- [character Model] = { card, direction, anim, startedAt, look }

local function hide(inst: Instance)
	if inst:IsA("BasePart") or inst:IsA("Decal") then
		inst.Transparency = 1
	end
end

local function untrack(character: Model)
	local t = tracked[character]
	if t then
		t.card:Destroy()
		tracked[character] = nil
	end
end

-- Paints a tracked character with its player's look; a new body needs a new card (different art).
local function applyLook(t, player: Player?)
	local look = Appearance.Decode(player and player:GetAttribute("Appearance"))
	local want = artFor(look.body)
	if not t.card or t.card.art ~= want then
		if t.card then
			t.card:Destroy()
		end
		t.card = SpriteCard.new(want, folder)
	end
	t.look = look
	t.card:SetLook(look)
end

local function track(character: Model)
	untrack(character)
	for _, d in ipairs(character:GetDescendants()) do
		hide(d)
	end
	character.DescendantAdded:Connect(hide)
	local t = { direction = "S", anim = "idle", startedAt = os.clock() }
	applyLook(t, Players:GetPlayerFromCharacter(character))
	tracked[character] = t
end

local function watch(player: Player)
	if player.Character then
		track(player.Character)
	end
	player.CharacterAdded:Connect(track)
	player.CharacterRemoving:Connect(untrack)
	player:GetAttributeChangedSignal("Appearance"):Connect(function()
		local t = player.Character and tracked[player.Character]
		if t then
			applyLook(t, player)
		end
	end)
end

for _, p in ipairs(Players:GetPlayers()) do
	watch(p)
end
Players.PlayerAdded:Connect(watch)

RunService:BindToRenderStep("CrownfallSprites", Enum.RenderPriority.Camera.Value + 2, function()
	local now = os.clock()
	for character, t in pairs(tracked) do
		local root = character.Parent and character:FindFirstChild("HumanoidRootPart")
		local humanoid = character:FindFirstChildOfClass("Humanoid")
		if not root or not humanoid then
			if not character.Parent then
				untrack(character)
			end
			continue
		end
		local velocity = root.AssemblyLinearVelocity * Vector3.new(1, 0, 1)
		local anim = SheetMath.AnimFor(velocity.Magnitude)
		local frame
		local dodgeStart = character:GetAttribute("DodgeStart")
		local sinceDodge = dodgeStart and workspace:GetServerTimeNow() - dodgeStart
		local art = t.card.art
		if art.Anims.dodge and sinceDodge and sinceDodge >= 0 and sinceDodge < Config.Movement.DodgeTime then
			-- a dodge roll: timed on the server clock so every client shows the same frame
			anim = "dodge"
			t.direction = character:GetAttribute("DodgeDir") or t.direction
			frame = SheetMath.FrameAt(art.Anims.dodge, sinceDodge)
		elseif anim ~= "idle" then
			t.direction = Facing.FromScreen(CameraMath.ToScreen(velocity))
		end
		if anim ~= t.anim then
			t.anim, t.startedAt = anim, now
		end
		if character == Players.LocalPlayer.Character then
			character:SetAttribute("Facing", t.direction) -- the dodge rolls this way when standing still
		end
		local def = art.Anims[anim] or art.Anims.idle
		t.card:Show(t.direction, anim, frame or SheetMath.FrameAt(def, now - t.startedAt))
		local foot = root.Position - Vector3.new(0, humanoid.HipHeight + root.Size.Y / 2, 0)
		t.card:Place(foot, camera.CFrame)
	end
end)
