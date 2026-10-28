-- Which art manifest draws each body (Shared/Appearance.Bodies). A body whose art isn't in yet uses the default.
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local Appearance = require(RS.Crownfall.Shared.Appearance)

local Arts = {}

local function module(name: string): ModuleScript?
	local folder = script.Parent:FindFirstChild("Art")
	local found = folder and folder:FindFirstChild(name)
	return if found and found:IsA("ModuleScript") then found else nil
end

local default = require(module(Config.Render.Art) or script.Parent.HeroSprite)
Arts.Default = default

-- True when this body's art is in the game.
function Arts.Has(bodyId: string): boolean
	local body = Appearance.FindBody(bodyId)
	return body ~= nil and module(body.Art) ~= nil
end

function Arts.For(bodyId: string?)
	local body = Appearance.FindBody(bodyId)
	local found = body and module(body.Art)
	return if found then require(found) else default
end

return Arts
