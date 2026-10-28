-- Q: dodge roll in the direction you're moving (or facing, when standing still). Moves the character
-- 2.5 studs over 0.4 s, fast out and easing into the landing, and marks frames 2-5 Invulnerable.
-- Stamina cost arrives with the Movement milestone (M2).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local Dodge = require(RS.Crownfall.Shared.Dodge)
local Facing = require(RS.Crownfall.Render.Facing)
local CameraMath = require(RS.Crownfall.Render.CameraMath)

local remote = RS:WaitForChild("CrownfallDodge")
local player = Players.LocalPlayer
local readyAt = 0

local function roll()
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local root = character and character:FindFirstChild("HumanoidRootPart")
	local attachment = root and root:FindFirstChild("RootAttachment")
	if not (humanoid and attachment) or humanoid.Health <= 0 then
		return
	end
	local startedAt = workspace:GetServerTimeNow()
	if startedAt < readyAt then
		return
	end
	readyAt = startedAt + Config.Movement.DodgeTime + Config.Movement.DodgeRecovery

	local move = humanoid.MoveDirection * Vector3.new(1, 0, 1)
	local direction = if move.Magnitude > 0.1
		then Facing.FromScreen(CameraMath.ToScreen(move))
		else (character:GetAttribute("Facing") or "S")
	character:SetAttribute("DodgeDir", direction) -- draw it at once; the server's copy reaches everyone else
	character:SetAttribute("DodgeStart", startedAt)
	remote:FireServer(direction, startedAt)

	local push = Instance.new("LinearVelocity")
	push.Attachment0 = attachment
	push.RelativeTo = Enum.ActuatorRelativeTo.World
	push.VelocityConstraintMode = Enum.VelocityConstraintMode.Plane
	push.PrimaryTangentAxis = Vector3.xAxis
	push.SecondaryTangentAxis = Vector3.zAxis
	push.MaxForce = math.huge
	push.Parent = root
	local along = Dodge.Vector(direction)
	local step
	step = RunService.Heartbeat:Connect(function()
		local elapsed = workspace:GetServerTimeNow() - startedAt
		if elapsed >= Config.Movement.DodgeTime or not push.Parent then
			step:Disconnect()
			push:Destroy()
			character:SetAttribute("Invulnerable", false)
			return
		end
		local v = along * Dodge.Speed(elapsed)
		push.PlaneVelocity = Vector2.new(v.X, v.Z)
		character:SetAttribute("Invulnerable", Dodge.Invulnerable(elapsed))
	end)
end

UserInputService.InputBegan:Connect(function(input, processed)
	if not processed and input.KeyCode == Enum.KeyCode.Q then
		roll()
	end
end)
