-- Loads, checks, saves and shares each player's creation choices (Shared/Profile): look, class, origin, traits.
-- They ride on the Player as attributes ("Appearance", "Class", "Origin", "Traits"), so every client sees them.
-- "AppearanceChosen" is false until the player has finished the creator once: the client then opens it.
-- Origin and traits are accepted only on that first finish; look and class can change later.
-- Each spawn puts the character at its origin's start (workspace.CrownfallOriginSpawns.<id>, else the default).
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local Origins = require(RS.Crownfall.Shared.Origins)
local Profile = require(RS.Crownfall.Shared.Profile)

local STORE_NAME = "CrownfallAppearance_v1"
local MIN_INTERVAL = 1 -- seconds between accepted changes per player
local SPAWN_LIFT = Vector3.new(0, 3, 0) -- from the top of a spawn pad to the character's root

local remote = Instance.new("RemoteEvent")
remote.Name = "CrownfallAppearance"
remote.Parent = RS

local store = nil
do
	local ok, result = pcall(DataStoreService.GetDataStore, DataStoreService, STORE_NAME)
	if ok then
		store = result
	else
		warn("[Crownfall] appearance saving off: " .. tostring(result))
	end
end

local profiles = {} -- [Player] = Profile
local lastChange = {} -- [Player] = os.clock()

local function keyFor(player: Player): string
	return "u" .. player.UserId
end

local function publish(player: Player, profile)
	profiles[player] = profile
	player:SetAttribute("Appearance", profile.look)
	player:SetAttribute("Class", profile.class)
	player:SetAttribute("Origin", profile.origin)
	player:SetAttribute("Traits", Profile.EncodeTraits(profile.traits))
end

local function spawnPoint(originId: string): Vector3
	local folder = workspace:FindFirstChild("CrownfallOriginSpawns")
	local pad = folder and folder:FindFirstChild(originId)
	if pad and pad:IsA("BasePart") then
		return pad.Position + Vector3.new(0, pad.Size.Y / 2, 0) + SPAWN_LIFT
	end
	local origin = Origins.Find(originId) or Origins.Find(Origins.Default)
	return origin.Spawn
end

local function placeAtOrigin(player: Player)
	local character = player.Character
	if character and player:GetAttribute("AppearanceChosen") then
		character:PivotTo(CFrame.new(spawnPoint(player:GetAttribute("Origin") or Origins.Default)))
	end
end

-- AppearanceChosen is set once, after loading, so the client never opens the creator on a stale "false".
-- If the save can't be read, the player keeps the defaults and isn't forced through the creator again.
local function load(player: Player)
	publish(player, Profile.Default())
	if not store then
		player:SetAttribute("AppearanceChosen", false)
		return
	end
	local ok, saved = pcall(store.GetAsync, store, keyFor(player))
	if not player.Parent then
		return
	end
	if not ok then
		warn("[Crownfall] could not load appearance: " .. tostring(saved))
	elseif saved ~= nil then
		publish(player, Profile.Sanitize(saved))
	end
	player:SetAttribute("AppearanceChosen", not ok or saved ~= nil)
	placeAtOrigin(player)
end

local function save(player: Player, profile)
	if not store then
		return
	end
	local ok, err = pcall(store.SetAsync, store, keyFor(player), Profile.ToSave(profile), { player.UserId })
	if not ok then
		warn("[Crownfall] could not save appearance: " .. tostring(err))
	end
end

-- request: { look, class, origin, traits } (origin and traits only count on the first finish).
remote.OnServerEvent:Connect(function(player: Player, request: any)
	if type(request) ~= "table" or not profiles[player] or player:GetAttribute("AppearanceChosen") == nil then
		return
	end
	local now = os.clock()
	if now - (lastChange[player] or -math.huge) < MIN_INTERVAL then
		return
	end
	lastChange[player] = now
	local firstTime = player:GetAttribute("AppearanceChosen") == false
	if firstTime and not Profile.ValidTraits(request.traits) then
		return -- the creator only finishes with both traits picked
	end
	local profile = Profile.Apply(profiles[player], request, firstTime)
	publish(player, profile)
	player:SetAttribute("AppearanceChosen", true)
	if firstTime then
		placeAtOrigin(player)
	end
	task.spawn(save, player, profile)
end)

local function watch(player: Player)
	player.CharacterAdded:Connect(function()
		task.defer(placeAtOrigin, player)
	end)
	load(player)
end

Players.PlayerAdded:Connect(watch)
for _, player in ipairs(Players:GetPlayers()) do
	task.spawn(watch, player)
end
Players.PlayerRemoving:Connect(function(player)
	profiles[player] = nil
	lastChange[player] = nil
end)
