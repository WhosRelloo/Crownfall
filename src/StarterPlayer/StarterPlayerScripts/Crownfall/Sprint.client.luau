-- Walk by default; hold Sprint (Left Shift) to run. Speeds live in Config.Movement.
-- Minimal stand-in until the Movement milestone (M2) adds stamina and dodge.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)

local player = Players.LocalPlayer

RunService.Heartbeat:Connect(function()
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid then
		return
	end
	local sprinting = UserInputService:IsKeyDown(Enum.KeyCode.LeftShift)
	humanoid.WalkSpeed = if sprinting then Config.Movement.SprintSpeed else Config.Movement.WalkSpeed
end)
