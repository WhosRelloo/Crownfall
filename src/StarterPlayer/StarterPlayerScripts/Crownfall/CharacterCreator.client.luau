-- The character creator (Docs/Character-Customization.md): presets first, then edit anything, with a large
-- animated preview you can turn through all 8 directions. Opens on first join (until a look is confirmed);
-- C reopens it for now, until the Barber and Tailor exist.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local Appearance = require(RS.Crownfall.Shared.Appearance)
local Render = RS.Crownfall.Render
local Arts = require(Render.Arts)
local Recolour = require(Render.Recolour)
local SheetMath = require(Render.SheetMath)

local player = Players.LocalPlayer
local remote = RS:WaitForChild("CrownfallAppearance")

local REOPEN_KEY = Enum.KeyCode.C
local DIRECTIONS = { "S", "SW", "W", "NW", "N", "NE", "E", "SE" }
local DIRECTION_NAMES = {
	S = "South", SW = "South-west", W = "West", NW = "North-west",
	N = "North", NE = "North-east", E = "East", SE = "South-east",
}
local ANIMS = { { "idle", "Idle" }, { "walk", "Walk" }, { "run", "Sprint" }, { "dodge", "Dodge" } }
local DODGE_REST = 0.6 -- seconds the preview holds the last dodge frame before rolling again
local PREVIEW_SCALE = 4 -- screen px per sprite px

-- Look and feel: warm charcoal panels, aged-gold trim, parchment text.
local C = {
	backdrop = Color3.fromRGB(9, 8, 7),
	panel = Color3.fromRGB(24, 20, 17),
	panelHi = Color3.fromRGB(36, 30, 25),
	inset = Color3.fromRGB(14, 12, 10),
	gold = Color3.fromRGB(201, 164, 98),
	goldDim = Color3.fromRGB(110, 88, 56),
	text = Color3.fromRGB(233, 221, 196),
	muted = Color3.fromRGB(150, 136, 114),
	edge = Color3.fromRGB(58, 48, 38),
}
local TITLE = Enum.Font.Fondamento
local BODY = Enum.Font.BuilderSansMedium
local BOLD = Enum.Font.BuilderSansBold

local function new(class: string, props: { [string]: any }, children: { Instance }?)
	local inst = Instance.new(class)
	for k, v in pairs(props) do
		if k ~= "Parent" then
			(inst :: any)[k] = v
		end
	end
	for _, child in ipairs(children or {}) do
		child.Parent = inst
	end
	inst.Parent = props.Parent
	return inst
end

local function corner(r: number)
	return new("UICorner", { CornerRadius = UDim.new(0, r) })
end

local function stroke(color: Color3, thickness: number?)
	return new("UIStroke", { Color = color, Thickness = thickness or 1, ApplyStrokeMode = Enum.ApplyStrokeMode.Border })
end

local function label(props)
	props.BackgroundTransparency = 1
	props.TextColor3 = props.TextColor3 or C.text
	props.Font = props.Font or BODY
	props.TextXAlignment = props.TextXAlignment or Enum.TextXAlignment.Left
	return new("TextLabel", props)
end

local function panel(props, children)
	props.BackgroundColor3 = props.BackgroundColor3 or C.panel
	props.BorderSizePixel = 0
	local list = { corner(6), stroke(C.edge) }
	for _, c in ipairs(children or {}) do
		table.insert(list, c)
	end
	return new("Frame", props, list)
end

-- A text button with hover and press feedback. kind: "plain" or "gold".
local function button(props, kind: string?)
	local gold = kind == "gold"
	local base = if gold then C.gold else C.panelHi
	props.BackgroundColor3 = base
	props.AutoButtonColor = false
	props.BorderSizePixel = 0
	props.Font = props.Font or BOLD
	props.TextColor3 = if gold then C.inset else C.text
	props.TextSize = props.TextSize or 16
	local b = new("TextButton", props, { corner(5), stroke(if gold then C.gold else C.edge) })
	local outline = b:FindFirstChildOfClass("UIStroke")
	b.MouseEnter:Connect(function()
		if b.Active then
			b.BackgroundColor3 = base:Lerp(Color3.new(1, 1, 1), 0.08)
			outline.Color = C.gold
		end
	end)
	b.MouseLeave:Connect(function()
		b.BackgroundColor3 = base
		outline.Color = if gold or b:GetAttribute("Selected") then C.gold else C.edge
	end)
	return b
end

-- The colour a swatch shows: a light-middle stop, so dark dyes still read apart on a dark panel.
local function swatchColour(ramp: { Color3 }): Color3
	return ramp[#ramp - 1]
end

-- State ------------------------------------------------------------------------------------------------------

local look = Appearance.Decode(player:GetAttribute("Appearance"))
local direction, anim, animStarted = "S", "idle", os.clock()
local gui: ScreenGui? = nil
local refreshers = {} -- functions that redraw selection state after the look changes
-- While a menu is open the character stands still (Sprint.client holds walk speed at 0) and can't jump.
local function holdStill(on: boolean)
	player:SetAttribute("InMenu", if on then true else nil)
	local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, not on)
	end
end

local function setLook(newLook)
	look = Appearance.Sanitize(newLook)
	for _, refresh in ipairs(refreshers) do
		refresh()
	end
	Recolour.Prepare(Arts.For(look.body), look)
end

-- Building the screen ----------------------------------------------------------------------------------------

local function swatchRow(parent: Instance, slot: string, title: string, y: number): number
	local options = Appearance.Options[slot]
	local perRow, size, gap = 8, 32, 7
	local rows = math.ceil(#options / perRow)

	label({ Parent = parent, Text = string.upper(title), Font = BOLD, TextSize = 13, TextColor3 = C.muted,
		Position = UDim2.fromOffset(18, y), Size = UDim2.fromOffset(120, 18) })
	local chosen = label({ Parent = parent, Text = "", TextSize = 15, TextXAlignment = Enum.TextXAlignment.Right,
		Position = UDim2.fromOffset(110, y), Size = UDim2.fromOffset(156, 18) })
	local dice = button({ Parent = parent, Text = "Roll", TextSize = 12, Position = UDim2.fromOffset(276, y - 3),
		Size = UDim2.fromOffset(44, 22) })
	dice.MouseButton1Click:Connect(function()
		setLook(Appearance.Random(Random.new(), look, slot))
	end)

	local cells = {}
	for i, entry in ipairs(options) do
		local col, row = (i - 1) % perRow, (i - 1) // perRow
		local cell = new("TextButton", {
			Parent = parent, Text = "", AutoButtonColor = false, BorderSizePixel = 0,
			BackgroundColor3 = Color3.new(1, 1, 1), -- the gradient paints it
			Position = UDim2.fromOffset(18 + col * (size + gap), y + 24 + row * (size + gap)),
			Size = UDim2.fromOffset(size, size),
		}, {
			corner(5),
			new("UIGradient", { Rotation = 35, Color = ColorSequence.new({
				ColorSequenceKeypoint.new(0, entry.Ramp[#entry.Ramp]),
				ColorSequenceKeypoint.new(0.5, entry.Ramp[#entry.Ramp - 1]),
				ColorSequenceKeypoint.new(1, entry.Ramp[3]),
			}) }),
			stroke(C.inset, 2),
		})
		local ring = cell:FindFirstChildOfClass("UIStroke")
		cell.MouseEnter:Connect(function()
			chosen.Text = entry.Name
			if look[slot] ~= entry.Id then
				ring.Color = C.goldDim
			end
		end)
		cell.MouseLeave:Connect(function()
			local current = Appearance.Find(slot, look[slot])
			chosen.Text = current and current.Name or ""
			if look[slot] ~= entry.Id then
				ring.Color = C.inset
			end
		end)
		cell.MouseButton1Click:Connect(function()
			local nextLook = table.clone(look)
			nextLook[slot] = entry.Id
			setLook(nextLook)
		end)
		cells[entry.Id] = { cell = cell, ring = ring }
	end

	table.insert(refreshers, function()
		for id, c in pairs(cells) do
			local on = look[slot] == id
			c.ring.Color = if on then C.gold else C.inset
			c.ring.Thickness = if on then 3 else 2
		end
		local current = Appearance.Find(slot, look[slot])
		chosen.Text = current and current.Name or ""
	end)
	return y + 24 + rows * (size + gap) + 10
end

local function build(firstTime: boolean)
	local screen = new("ScreenGui", {
		Name = "CrownfallCreator", ResetOnSpawn = false, IgnoreGuiInset = true, DisplayOrder = 50,
		ZIndexBehavior = Enum.ZIndexBehavior.Sibling, Parent = player:WaitForChild("PlayerGui"),
	})
	new("Frame", { Parent = screen, BackgroundColor3 = C.backdrop, BackgroundTransparency = 0.12,
		BorderSizePixel = 0, Size = UDim2.fromScale(1, 1) })

	-- everything is laid out at 1120 x 660 and scaled to fit the screen
	local root = new("Frame", { Name = "Root", Parent = screen, BackgroundTransparency = 1, AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(1120, 660) })
	local scale = new("UIScale", { Parent = root })
	local function fit()
		local view = (workspace.CurrentCamera :: Camera).ViewportSize
		scale.Scale = math.min(view.X / 1180, view.Y / 700, 1.4)
	end
	fit()
	table.insert(refreshers, fit)
	local fitConn = (workspace.CurrentCamera :: Camera):GetPropertyChangedSignal("ViewportSize"):Connect(fit)

	label({ Parent = root, Text = if firstTime then "Forge your wanderer" else "Change your look",
		Font = TITLE, TextSize = 40, TextColor3 = C.gold, Size = UDim2.fromOffset(700, 46) })
	label({ Parent = root, Text = "Start from a look below, then make it yours. Hair and dyes can be changed later in town.",
		TextSize = 16, TextColor3 = C.muted, Position = UDim2.fromOffset(2, 46), Size = UDim2.fromOffset(900, 20) })

	-- Presets (left)
	local presets = panel({ Name = "Presets", Parent = root, Position = UDim2.fromOffset(0, 84), Size = UDim2.fromOffset(250, 576) })
	label({ Parent = presets, Text = "PRESETS", Font = BOLD, TextSize = 13, TextColor3 = C.muted,
		Position = UDim2.fromOffset(16, 12), Size = UDim2.fromOffset(200, 18) })
	local presetButtons = {}
	for i, preset in ipairs(Appearance.Presets) do
		local b = button({ Name = "Preset_" .. i, Parent = presets, Text = "", Position = UDim2.fromOffset(12, 36 + (i - 1) * 56),
			Size = UDim2.fromOffset(226, 48) })
		label({ Parent = b, Text = preset.Name, Font = TITLE, TextSize = 20, Position = UDim2.fromOffset(12, 0),
			Size = UDim2.fromOffset(130, 48) })
		for j, slot in ipairs(Appearance.Slots) do
			local entry = Appearance.Find(slot, preset.Look[slot])
			new("Frame", { Parent = b, BorderSizePixel = 0, BackgroundColor3 = swatchColour(entry.Ramp),
				AnchorPoint = Vector2.new(0, 0.5), Position = UDim2.fromOffset(140 + (j - 1) * 26, 24),
				Size = UDim2.fromOffset(20, 20) }, { corner(10), stroke(C.inset, 2) })
		end
		b.MouseButton1Click:Connect(function()
			local nextLook = table.clone(preset.Look)
			nextLook.body = look.body
			setLook(nextLook)
		end)
		presetButtons[i] = { button = b, preset = preset }
	end
	table.insert(refreshers, function()
		for _, p in ipairs(presetButtons) do
			local same = true
			for _, slot in ipairs(Appearance.Slots) do
				same = same and look[slot] == p.preset.Look[slot]
			end
			p.button:SetAttribute("Selected", same)
			p.button:FindFirstChildOfClass("UIStroke").Color = if same then C.gold else C.edge
		end
	end)
	local random = button({ Parent = presets, Text = "Randomize all", Position = UDim2.fromOffset(12, 520),
		Size = UDim2.fromOffset(226, 44) })
	random.MouseButton1Click:Connect(function()
		setLook(Appearance.Random(Random.new(), look))
	end)

	-- Preview (centre)
	local stage = panel({ Name = "Stage", Parent = root, BackgroundColor3 = Color3.new(1, 1, 1), Position = UDim2.fromOffset(266, 84),
		Size = UDim2.fromOffset(500, 576) })
	new("UIGradient", { Parent = stage, Rotation = 90, Color = ColorSequence.new(
		Color3.fromRGB(58, 50, 42), Color3.fromRGB(16, 13, 11)) }) -- a lamp-lit floor fading into the dark
	new("Frame", { Parent = stage, BorderSizePixel = 0, BackgroundColor3 = Color3.fromRGB(0, 0, 0),
		BackgroundTransparency = 0.55, AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromOffset(250, 401),
		Size = UDim2.fromOffset(150, 26) }, { corner(13) }) -- ground shadow under the feet
	local sprite = new("ImageLabel", { Parent = stage, BackgroundTransparency = 1,
		ResampleMode = Enum.ResamplerMode.Pixelated, Size = UDim2.fromOffset(96 * PREVIEW_SCALE, 96 * PREVIEW_SCALE) })
	local painting = label({ Parent = stage, Text = "Painting…", TextSize = 14, TextColor3 = C.muted,
		TextXAlignment = Enum.TextXAlignment.Right, Position = UDim2.fromOffset(300, 12), Size = UDim2.fromOffset(186, 18) })

	local turnLeft = button({ Name = "TurnLeft", Parent = stage, Text = "◀", TextSize = 18, Position = UDim2.fromOffset(110, 448),
		Size = UDim2.fromOffset(44, 36) })
	local turnRight = button({ Name = "TurnRight", Parent = stage, Text = "▶", TextSize = 18, Position = UDim2.fromOffset(346, 448),
		Size = UDim2.fromOffset(44, 36) })
	local facing = label({ Parent = stage, Text = "", Font = TITLE, TextSize = 20, TextXAlignment = Enum.TextXAlignment.Center,
		Position = UDim2.fromOffset(160, 448), Size = UDim2.fromOffset(180, 36) })
	local function turn(step: number)
		local i = table.find(DIRECTIONS, direction) :: number
		direction = DIRECTIONS[(i - 1 + step) % #DIRECTIONS + 1]
		facing.Text = DIRECTION_NAMES[direction]
	end
	turnLeft.MouseButton1Click:Connect(function()
		turn(-1)
	end)
	turnRight.MouseButton1Click:Connect(function()
		turn(1)
	end)
	turn(0)

	local animButtons = {}
	for i, a in ipairs(ANIMS) do
		local b = button({ Name = "Anim_" .. a[1], Parent = stage, Text = a[2], TextSize = 15, Position = UDim2.fromOffset(34 + (i - 1) * 110, 506),
			Size = UDim2.fromOffset(102, 40) })
		b.MouseButton1Click:Connect(function()
			anim, animStarted = a[1], os.clock()
			for _, other in ipairs(animButtons) do
				other.TextColor3 = if other == b then C.gold else C.text
				other:SetAttribute("Selected", other == b)
				other:FindFirstChildOfClass("UIStroke").Color = if other == b then C.gold else C.edge
			end
		end)
		animButtons[i] = b
		b.TextColor3 = if a[1] == anim then C.gold else C.text
		b:SetAttribute("Selected", a[1] == anim)
		b:FindFirstChildOfClass("UIStroke").Color = if a[1] == anim then C.gold else C.edge
	end

	-- Options (right)
	local options = panel({ Name = "Options", Parent = root, Position = UDim2.fromOffset(782, 84), Size = UDim2.fromOffset(338, 500) })
	label({ Parent = options, Text = "BODY", Font = BOLD, TextSize = 13, TextColor3 = C.muted,
		Position = UDim2.fromOffset(18, 14), Size = UDim2.fromOffset(120, 18) })
	local bodyButtons = {}
	for i, body in ipairs(Appearance.Bodies) do
		local has = Arts.Has(body.Id)
		local b = button({ Name = "Body_" .. body.Id, Parent = options, Text = body.Name, TextSize = 16,
			Position = UDim2.fromOffset(18 + (i - 1) * 154, 38), Size = UDim2.fromOffset(146, 40) })
		if not has then
			b.Active = false
			b.TextColor3 = C.muted
			label({ Parent = b, Text = "ART COMING", Font = BOLD, TextSize = 10, TextColor3 = C.goldDim,
				TextXAlignment = Enum.TextXAlignment.Center, Position = UDim2.fromOffset(0, 27), Size = UDim2.fromOffset(146, 12) })
		end
		b.MouseButton1Click:Connect(function()
			if has then
				local nextLook = table.clone(look)
				nextLook.body = body.Id
				setLook(nextLook)
			end
		end)
		bodyButtons[body.Id] = b
	end
	table.insert(refreshers, function()
		for id, b in pairs(bodyButtons) do
			b:SetAttribute("Selected", look.body == id)
			b:FindFirstChildOfClass("UIStroke").Color = if look.body == id then C.gold else C.edge
		end
	end)

	local y = 96
	y = swatchRow(options, "skin", "Skin", y)
	y = swatchRow(options, "hair", "Hair", y)
	swatchRow(options, "outfit", "Outfit dye", y)

	-- Confirm (and cancel when reopened)
	local confirm = button({ Name = "Confirm", Parent = root, Text = if firstTime then "Begin" else "Save look", Font = TITLE, TextSize = 26,
		Position = UDim2.fromOffset(if firstTime then 782 else 958, 598), Size = UDim2.fromOffset(if firstTime then 338 else 162, 62) }, "gold")
	local cancel = nil
	local before = table.clone(look)
	if not firstTime then
		cancel = button({ Name = "Cancel", Parent = root, Text = "Cancel", TextSize = 18, Position = UDim2.fromOffset(782, 598),
			Size = UDim2.fromOffset(162, 62) })
	end

	-- live preview
	local renderConn = RunService.RenderStepped:Connect(function()
		local art = Arts.For(look.body)
		local useAnim = if art.Anims[anim] then anim else "idle"
		local def = art.Anims[useAnim]
		local elapsed = os.clock() - animStarted
		if def.Mode == "Once" then -- replay the roll after a short rest
			elapsed %= def.Frames / def.FPS + DODGE_REST
		end
		local frame = SheetMath.FrameAt(def, elapsed)
		local rect = SheetMath.Rect(def, direction, frame, art.Cell, art.Pivot)
		local painted = Recolour.Get(art, look, useAnim, direction)
		sprite.ImageContent = painted
			or Content.fromUri(SheetMath.Image(def, direction) or art.Layers.full[art.Outfit][useAnim])
		sprite.ImageRectOffset = rect.Offset
		sprite.ImageRectSize = rect.Size
		-- stand the feet pivot on the shadow
		sprite.Position = UDim2.fromOffset(250 - rect.Pivot.X * PREVIEW_SCALE, 398 - rect.Pivot.Y * PREVIEW_SCALE)
		painting.Visible = painted == nil and not Appearance.IsDrawn(look)
	end)

	local function close(save: boolean)
		renderConn:Disconnect()
		fitConn:Disconnect()
		table.clear(refreshers)
		screen:Destroy()
		gui = nil
		holdStill(false)
		if save then
			remote:FireServer(Appearance.Encode(look))
		else
			look = before
		end
	end
	confirm.MouseButton1Click:Connect(function()
		close(true)
	end)
	if cancel then
		cancel.MouseButton1Click:Connect(function()
			close(false)
		end)
	end

	holdStill(true)
	gui = screen
	setLook(look)
end

local function open(firstTime: boolean)
	if gui then
		return
	end
	look = Appearance.Decode(player:GetAttribute("Appearance"))
	build(firstTime)
end

-- First join: wait for the server to say whether a look was ever confirmed.
task.spawn(function()
	while player:GetAttribute("AppearanceChosen") == nil do
		player:GetAttributeChangedSignal("AppearanceChosen"):Wait()
	end
	if player:GetAttribute("AppearanceChosen") == false then
		open(true)
	end
end)

UserInputService.InputBegan:Connect(function(input, processed)
	if not processed and input.KeyCode == REOPEN_KEY and not gui then
		open(false)
	end
end)
