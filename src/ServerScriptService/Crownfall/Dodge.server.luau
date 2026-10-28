-- Accepts dodge rolls and marks them on the character (DodgeDir, DodgeStart in server time), so every
-- client draws the same roll. The rolling player's own client moves the character (it owns its physics).
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)

local remote = Instance.new("RemoteEvent")
remote.Name = "CrownfallDodge"
remote.Parent = RS

local DIRECTIONS = { S = true, SW = true, W = true, NW = true, N = true, NE = true, E = true, SE = true }
local MAX_CLOCK_SKEW = 0.3 -- seconds a client's start time may differ from the server's clock

remote.OnServerEvent:Connect(function(player: Player, direction: any, startedAt: any)
	if typeof(direction) ~= "string" or not DIRECTIONS[direction] or typeof(startedAt) ~= "number" then
		return
	end
	local character = player.Character
	if not character then
		return
	end
	local now = workspace:GetServerTimeNow()
	if math.abs(now - startedAt) > MAX_CLOCK_SKEW then
		startedAt = now
	end
	local last = character:GetAttribute("DodgeStart") or -math.huge
	if startedAt - last < Config.Movement.DodgeTime + Config.Movement.DodgeRecovery - 0.05 then
		return -- still rolling or recovering
	end
	character:SetAttribute("DodgeDir", direction)
	character:SetAttribute("DodgeStart", startedAt)
end)


