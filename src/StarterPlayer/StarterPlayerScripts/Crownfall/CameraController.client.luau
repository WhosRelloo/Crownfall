-- Fixed three-quarter camera that follows the local character (blueprint: Platform assumption, 4.13).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local CameraMath = require(RS.Crownfall.Render.CameraMath)

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local offset = CameraMath.Offset(Config.Camera.Pitch, Config.Camera.Distance)
local focus: Vector3? = nil

RunService:BindToRenderStep("CrownfallCamera", Enum.RenderPriority.Camera.Value + 1, function(dt)
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then
		return
	end
	camera.CameraType = Enum.CameraType.Scriptable
	camera.FieldOfView = Config.Camera.FieldOfView
	local target = root.Position
	focus = if focus then focus:Lerp(target, math.min(dt * Config.Camera.FollowSharpness, 1)) else target
	camera.CFrame = CFrame.lookAt(focus + offset, focus)
end)
