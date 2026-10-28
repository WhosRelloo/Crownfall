-- A camera-facing card that draws one frame of a character. Client-side only.
-- Works with both art kinds: "Rows" (placeholder drawn in code) and "Sheet" (uploaded sprite sheets).
local PixelArt = require(script.Parent.PixelArt)
local SheetMath = require(script.Parent.SheetMath)
local Recolour = require(script.Parent.Recolour)

local ROWS_CANVAS_SCALE = 8 -- SurfaceGui pixels per placeholder pixel
local SHEET_CANVAS_SCALE = 4 -- SurfaceGui pixels per sheet pixel

local SpriteCard = {}
SpriteCard.__index = SpriteCard

local function frameSize(art): Vector2
	return if art.Kind == "Sheet" then Vector2.new(art.Cell, art.Cell) else Vector2.new(art.Width, art.Height)
end

function SpriteCard.new(art, parent: Instance)
	local size = frameSize(art)
	local part = Instance.new("Part")
	part.Name = "SpriteCard"
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1
	part.Size = Vector3.new(size.X * art.StudsPerPixel, size.Y * art.StudsPerPixel, 0.05)

	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	gui.CanvasSize = size * (if art.Kind == "Sheet" then SHEET_CANVAS_SCALE else ROWS_CANVAS_SCALE)
	gui.LightInfluence = 1
	gui.Parent = part

	local image = nil
	if art.Kind == "Sheet" then
		image = Instance.new("ImageLabel")
		image.BackgroundTransparency = 1
		image.Size = UDim2.fromScale(1, 1)
		image.ResampleMode = Enum.ResamplerMode.Pixelated
		image.Parent = gui
	end

	part.Parent = parent
	return setmetatable({ part = part, gui = gui, image = image, art = art, shown = nil, pivot = art.Pivot }, SpriteCard)
end

-- Paints this card with a look (Shared/Appearance); nil shows the drawn colours.
function SpriteCard:SetLook(look)
	self.look = look
	self.shown = nil
	if look and self.art.Kind == "Sheet" then
		Recolour.Prepare(self.art, look)
	end
end

-- Shows frame `frame` (1-based) of `anim` facing `direction`. Missing animations fall back to idle.
-- With a look set, shows the repainted image once it is baked and the drawn one until then.
function SpriteCard:Show(direction: string, anim: string, frame: number)
	local art = self.art
	if not art.Anims[anim] then
		anim = "idle"
		frame = 1
	end
	local painted = art.Kind == "Sheet" and self.look and Recolour.Get(art, self.look, anim, direction)
	local key = direction .. "/" .. anim .. "/" .. frame .. (if painted then "*" else "")
	if key == self.shown then
		return
	end
	self.shown = key

	if art.Kind == "Sheet" then
		local def = art.Anims[anim]
		local rect = SheetMath.Rect(def, direction, frame, art.Cell, art.Pivot)
		self.image.ImageContent = painted
			or Content.fromUri(SheetMath.Image(def, direction) or art.Layers.full[art.Outfit][anim])
		self.image.ImageRectOffset = rect.Offset
		self.image.ImageRectSize = rect.Size
		self.pivot = rect.Pivot
		return
	end

	local rows, mirror = art.Draw(direction, anim, frame)
	self.gui:ClearAllChildren()
	for _, run in ipairs(PixelArt.ToRuns(rows, mirror)) do
		local f = Instance.new("Frame")
		f.BorderSizePixel = 0
		f.BackgroundColor3 = art.Palette[run.key]
		f.Position = UDim2.fromScale(run.x / art.Width, run.y / art.Height)
		f.Size = UDim2.fromScale(run.w / art.Width, 1 / art.Height)
		f.Parent = self.gui
	end
	self.pivot = Vector2.new(if mirror then art.Width - art.Pivot.X else art.Pivot.X, art.Pivot.Y)
end

-- Stands the card so its feet pivot sits on `foot`, turned to face the camera so the sprite keeps its full height.
function SpriteCard:Place(foot: Vector3, cameraCFrame: CFrame)
	local size = frameSize(self.art)
	local s = self.art.StudsPerPixel
	local cf = CFrame.lookAt(foot, foot - cameraCFrame.LookVector)
	-- From the pivot pixel to the card centre, in screen terms (x right, y up). Seen from the camera, the
	-- front face's GUI runs along -RightVector, so screen-right is -RightVector.
	local dx = (size.X / 2 - self.pivot.X) * s
	local dy = (self.pivot.Y - size.Y / 2) * s
	self.part.CFrame = cf - cf.RightVector * dx + cf.UpVector * dy
end

function SpriteCard:Destroy()
	self.part:Destroy()
end

return SpriteCard
