-- Loads, checks, saves and shares each player's look (Shared/Appearance). The look rides on the Player as the
-- "Appearance" attribute (an encoded string), so every client paints everyone the same way.
-- "AppearanceChosen" is false until the player has confirmed a look once: the client then opens the creator.
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local Appearance = require(RS.Crownfall.Shared.Appearance)

local STORE_NAME = "CrownfallAppearance_v1"
local MIN_INTERVAL = 1 -- seconds between accepted changes per player

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

local lastChange = {} -- [Player] = os.clock()

local function keyFor(player: Player): string
	return "u" .. player.UserId
end

-- AppearanceChosen is set once, after loading, so the client never opens the creator on a stale "false".
-- If the save can't be read, the player keeps the default look and isn't forced through the creator again.
local function load(player: Player)
	player:SetAttribute("Appearance", Appearance.Encode(Appearance.Default))
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
	elseif type(saved) == "string" then
		player:SetAttribute("Appearance", Appearance.Encode(Appearance.Decode(saved)))
	end
	player:SetAttribute("AppearanceChosen", not ok or type(saved) == "string")
end

local function save(player: Player, encoded: string)
	if not store then
		return
	end
	local ok, err = pcall(store.SetAsync, store, keyFor(player), encoded, { player.UserId })
	if not ok then
		warn("[Crownfall] could not save appearance: " .. tostring(err))
	end
end

remote.OnServerEvent:Connect(function(player: Player, encoded: any)
	if type(encoded) ~= "string" or #encoded > 80 then
		return
	end
	local now = os.clock()
	if now - (lastChange[player] or -math.huge) < MIN_INTERVAL then
		return
	end
	lastChange[player] = now
	local clean = Appearance.Encode(Appearance.Decode(encoded))
	player:SetAttribute("Appearance", clean)
	player:SetAttribute("AppearanceChosen", true)
	task.spawn(save, player, clean)
end)

Players.PlayerAdded:Connect(load)
for _, player in ipairs(Players:GetPlayers()) do
	task.spawn(load, player)
end
Players.PlayerRemoving:Connect(function(player)
	lastChange[player] = nil
end)
