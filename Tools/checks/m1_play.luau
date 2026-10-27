-- Run in the Client datamodel while Place1 is in Play. Returns PASS/FAIL lines.
local Players = game:GetService("Players")
local lines, failed = {}, 0
local function check(ok, label)
	if not ok then failed += 1 end
	table.insert(lines, (ok and "PASS " or "FAIL ") .. label)
end

local camera = workspace.CurrentCamera
check(camera.CameraType == Enum.CameraType.Scriptable, "camera is Scriptable")
check(math.abs(camera.FieldOfView - 20) < 0.01, "camera FOV is 20")

local folder = workspace:FindFirstChild("CrownfallSprites")
check(folder ~= nil, "CrownfallSprites folder exists")
local card = folder and folder:FindFirstChild("SpriteCard")
check(card ~= nil, "a SpriteCard exists")
local gui = card and card:FindFirstChildOfClass("SurfaceGui")
local image = gui and gui:FindFirstChildOfClass("ImageLabel")
check(gui ~= nil and ((image ~= nil and image.Image ~= "") or #gui:GetChildren() > 10), "the card draws a frame")
if image then
	check(image.ResampleMode == Enum.ResamplerMode.Pixelated, "sheet frames are drawn pixelated")
end

local character = Players.LocalPlayer.Character
local head = character and character:FindFirstChild("Head")
check(head ~= nil and head.Transparency == 1, "the Roblox body is hidden")

if card and character and character:FindFirstChild("HumanoidRootPart") then
	local toCamera = (camera.CFrame.Position - card.Position).Unit
	check(card.CFrame.LookVector:Dot(toCamera) > 0.95, "the card faces the camera")
	local flat = (card.Position - character.HumanoidRootPart.Position) * Vector3.new(1, 0, 1)
	check(flat.Magnitude < 4, "the card stands on the character")
end

table.insert(lines, ("%d failed"):format(failed))
return table.concat(lines, "\n")
