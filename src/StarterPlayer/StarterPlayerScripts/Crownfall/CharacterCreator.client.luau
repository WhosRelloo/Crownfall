-- The character creator (Docs/Character-Customization.md, Docs/Plans/2026-10-28-class-origin-traits-hair.md):
-- four steps (Look, Class, Origin, Traits) around a large animated preview you can turn through all 8 directions.
-- Opens on first join (until the creator is finished once). C reopens it for now, as a stand-in for the shrine,
-- Barber and Tailor: look and class only, since origin and traits are fixed once chosen.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local Appearance = require(RS.Crownfall.Shared.Appearance)
local Classes = require(RS.Crownfall.Shared.Classes)
local Origins = require(RS.Crownfall.Shared.Origins)
local Traits = require(RS.Crownfall.Shared.Traits)
local Profile = require(RS.Crownfall.Shared.Profile)
local Render = RS.Crownfall.Render
local Arts = require(Render.Arts)
local Recolour = require(Render.Recolour)
local SheetMath = require(Render.SheetMath)
local HairLayer = require(Render.HairLayer)

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
	good = Color3.fromRGB(138, 196, 120),
	bad = Color3.fromRGB(214, 112, 96),
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
local refreshers = {} -- functions that redraw selection state after a choice changes
local choice = { class = Classes.Default, origin = Origins.Default, traits = {} } -- the non-look picks
-- While a menu is open the character stands still (Sprint.client holds walk speed at 0) and can't jump.
local function holdStill(on: boolean)
	player:SetAttribute("InMenu", if on then true else nil)
	local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, not on)
	end
end

local function refresh()
	for _, r in ipairs(refreshers) do
		r()
	end
end

local function setLook(newLook)
	look = Appearance.Sanitize(newLook)
	refresh()
	Recolour.Prepare(Arts.For(look.body), look)
end

local function sectionTitle(parent: Instance, text: string, x: number, y: number)
	return label({ Parent = parent, Text = string.upper(text), Font = BOLD, TextSize = 13, TextColor3 = C.muted,
		Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(240, 18) })
end

-- A column of pick buttons; isOn(item) says which are selected, onPick(item) handles a click.
local function pickList(parent: Instance, items, opts)
	local buttons = {}
	for i, item in ipairs(items) do
		local b = button({ Name = opts.prefix .. item.Id, Parent = parent, Text = "",
			Position = UDim2.fromOffset(12, opts.top + (i - 1) * opts.step), Size = UDim2.fromOffset(226, opts.height) })
		label({ Parent = b, Text = item.Name, Font = TITLE, TextSize = opts.titleSize or 20,
			Position = UDim2.fromOffset(12, if opts.sub then 6 else 0), Size = UDim2.fromOffset(204, if opts.sub then 28 else opts.height) })
		if opts.sub then
			label({ Parent = b, Text = opts.sub(item), TextSize = 13, TextColor3 = C.muted,
				Position = UDim2.fromOffset(12, opts.height - 26), Size = UDim2.fromOffset(204, 16) })
		end
		b.MouseButton1Click:Connect(function()
			opts.onPick(item)
			refresh()
		end)
		if opts.onHover then
			b.MouseEnter:Connect(function()
				opts.onHover(item)
			end)
		end
		buttons[item.Id] = b
	end
	table.insert(refreshers, function()
		for _, item in ipairs(items) do
			local b, on = buttons[item.Id], opts.isOn(item)
			b:SetAttribute("Selected", on)
			b:FindFirstChildOfClass("UIStroke").Color = if on then C.gold else C.edge
		end
	end)
	return buttons
end

-- "Label: value" rows for a card.
local function factRow(parent: Instance, y: number, name: string, value: string)
	label({ Parent = parent, Text = name, TextSize = 14, TextColor3 = C.muted, Position = UDim2.fromOffset(18, y),
		Size = UDim2.fromOffset(110, 20) })
	return label({ Parent = parent, Text = value, Font = BOLD, TextSize = 15, Position = UDim2.fromOffset(128, y),
		Size = UDim2.fromOffset(196, 20), TextTruncate = Enum.TextTruncate.AtEnd })
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
		Font = TITLE, TextSize = 40, TextColor3 = C.gold, Size = UDim2.fromOffset(520, 46) })
	local subtitle = label({ Parent = root, Text = "", TextSize = 16, TextColor3 = C.muted,
		Position = UDim2.fromOffset(2, 46), Size = UDim2.fromOffset(760, 20) })

	-- Steps: each shows its own left and right panels; the preview in the middle stays.
	local STEPS = if firstTime
		then { { "look", "Look" }, { "class", "Class" }, { "origin", "Origin" }, { "traits", "Traits" } }
		else { { "look", "Look" }, { "class", "Class" } }
	local HINTS = {
		look = "Start from a look, then make it yours. Hair and dyes can be changed later in town.",
		class = "Your starting role and kit. You can switch class at any shrine.",
		origin = "Where you come from, and where you wake after the opening. This stays with you.",
		traits = "Pick " .. Traits.Pick .. ". Each has an upside and a cost. These stay with you.",
	}
	local step = 1
	local stepPanels = {} -- [step id] = { panels }
	local stepTabs = {}
	for i, s in ipairs(STEPS) do
		local tab = button({ Name = "Step_" .. s[1], Parent = root, Text = i .. "  " .. s[2], TextSize = 15,
			Position = UDim2.fromOffset(1120 - (#STEPS - i + 1) * 112 + 8, 10), Size = UDim2.fromOffset(104, 34) })
		stepTabs[i] = tab
	end
	for _, id in ipairs({ "look", "class", "origin", "traits" }) do
		stepPanels[id] = {}
	end
	local function own(stepId: string, inst: Instance)
		table.insert(stepPanels[stepId], inst)
		return inst
	end

	-- Presets (left)
	local presets = own("look", panel({ Name = "Presets", Parent = root, Position = UDim2.fromOffset(0, 84), Size = UDim2.fromOffset(250, 576) }))
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
			nextLook.body, nextLook.style = look.body, look.style
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
	local hairSprite = new("ImageLabel", { Name = "Hair", Parent = sprite, BackgroundTransparency = 1, ZIndex = 2,
		ResampleMode = Enum.ResamplerMode.Pixelated, Visible = false })
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
	local options = own("look", panel({ Name = "Options", Parent = root, Position = UDim2.fromOffset(782, 84), Size = UDim2.fromOffset(338, 500) }))
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
	y = swatchRow(options, "outfit", "Outfit dye", y)

	-- Hairstyle: cycles through the styles of this body whose art is in the game
	local function styles()
		local list = {}
		for _, entry in ipairs(Appearance.Hairstyles[look.body] or {}) do
			if HairLayer.For(Arts.For(look.body), entry.Id) then
				table.insert(list, entry)
			end
		end
		return list
	end
	sectionTitle(options, "Hairstyle", 18, y)
	local styleName = label({ Parent = options, Text = "", Font = TITLE, TextSize = 20, TextXAlignment = Enum.TextXAlignment.Center,
		Position = UDim2.fromOffset(64, y + 22), Size = UDim2.fromOffset(210, 30) })
	local prevStyle = button({ Name = "StylePrev", Parent = options, Text = "◀", TextSize = 16, Position = UDim2.fromOffset(18, y + 22),
		Size = UDim2.fromOffset(40, 30) })
	local nextStyle = button({ Name = "StyleNext", Parent = options, Text = "▶", TextSize = 16, Position = UDim2.fromOffset(280, y + 22),
		Size = UDim2.fromOffset(40, 30) })
	local function cycle(step: number)
		local list = styles()
		if #list == 0 then
			return
		end
		local at = 1
		for i, entry in ipairs(list) do
			if entry.Id == look.style then
				at = i
			end
		end
		local nextLook = table.clone(look)
		nextLook.style = list[(at - 1 + step) % #list + 1].Id
		setLook(nextLook)
	end
	prevStyle.MouseButton1Click:Connect(function()
		cycle(-1)
	end)
	nextStyle.MouseButton1Click:Connect(function()
		cycle(1)
	end)
	table.insert(refreshers, function()
		local list = styles()
		local current = Appearance.FindStyle(look.body, look.style)
		styleName.Text = if #list > 1 and current then current.Name else "More styles soon"
		prevStyle.Visible, nextStyle.Visible = #list > 1, #list > 1
	end)

	-- Class step ------------------------------------------------------------------------------------------------
	local classLeft = own("class", panel({ Name = "ClassList", Parent = root, Position = UDim2.fromOffset(0, 84), Size = UDim2.fromOffset(250, 576) }))
	sectionTitle(classLeft, "Class", 16, 12)
	pickList(classLeft, Classes.List, {
		prefix = "Class_", top = 36, step = 88, height = 80, titleSize = 22,
		sub = function(c)
			return c.Weapon .. "  ·  " .. c.Armour
		end,
		isOn = function(c)
			return choice.class == c.Id
		end,
		onPick = function(c)
			choice.class = c.Id
		end,
	})
	local classCard = own("class", panel({ Name = "ClassCard", Parent = root, Position = UDim2.fromOffset(782, 84), Size = UDim2.fromOffset(338, 500) }))
	local className = label({ Parent = classCard, Text = "", Font = TITLE, TextSize = 32, TextColor3 = C.gold,
		Position = UDim2.fromOffset(18, 14), Size = UDim2.fromOffset(300, 40) })
	local classRole = label({ Parent = classCard, Text = "", TextSize = 16, TextWrapped = true,
		TextYAlignment = Enum.TextYAlignment.Top, Position = UDim2.fromOffset(18, 60), Size = UDim2.fromOffset(302, 88) })
	sectionTitle(classCard, "Starting kit", 18, 160)
	local facts = {
		Weapon = factRow(classCard, 186, "Weapon", ""),
		Armour = factRow(classCard, 212, "Armour", ""),
		Power = factRow(classCard, 238, "First power", ""),
		Discipline = factRow(classCard, 264, "Discipline", ""),
	}
	label({ Parent = classCard, Text = "Switch class any time at a shrine. Weapons other than the longsword are drawn when combat arrives; until then every class carries the longsword.",
		TextSize = 13, TextColor3 = C.muted, TextWrapped = true, TextYAlignment = Enum.TextYAlignment.Top,
		Position = UDim2.fromOffset(18, 420), Size = UDim2.fromOffset(302, 64) })
	table.insert(refreshers, function()
		local c = Classes.Find(choice.class)
		className.Text = c.Name
		classRole.Text = c.Role
		for field, l in pairs(facts) do
			l.Text = c[field]
		end
	end)

	-- Origin step -----------------------------------------------------------------------------------------------
	local originLeft = own("origin", panel({ Name = "OriginList", Parent = root, Position = UDim2.fromOffset(0, 84), Size = UDim2.fromOffset(250, 576) }))
	sectionTitle(originLeft, "Origin", 16, 12)
	pickList(originLeft, Origins.List, {
		prefix = "Origin_", top = 36, step = 106, height = 96, titleSize = 21,
		sub = function(o)
			return o.Homeland
		end,
		isOn = function(o)
			return choice.origin == o.Id
		end,
		onPick = function(o)
			choice.origin = o.Id
		end,
	})
	local originCard = own("origin", panel({ Name = "OriginCard", Parent = root, Position = UDim2.fromOffset(782, 84), Size = UDim2.fromOffset(338, 500) }))
	-- a small map of the Reach: parchment-dark ground, the Scar in the south-east, one marker per homeland
	local map = new("Frame", { Name = "Map", Parent = originCard, BorderSizePixel = 0, BackgroundColor3 = Color3.new(1, 1, 1),
		Position = UDim2.fromOffset(18, 16), Size = UDim2.fromOffset(302, 170) }, {
		corner(5), stroke(C.edge),
		new("UIGradient", { Rotation = 60, Color = ColorSequence.new(Color3.fromRGB(64, 56, 44), Color3.fromRGB(34, 29, 24)) }),
	})
	new("Frame", { Parent = map, BorderSizePixel = 0, BackgroundColor3 = Color3.fromRGB(96, 58, 120), BackgroundTransparency = 0.55,
		AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.82, 0.78), Size = UDim2.fromOffset(46, 20) }, { corner(10) })
	label({ Parent = map, Text = "the Scar", TextSize = 11, TextColor3 = Color3.fromRGB(186, 160, 206), TextXAlignment = Enum.TextXAlignment.Center,
		AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.82, 0, 0.78, 11), Size = UDim2.fromOffset(60, 12) })
	local markers = {}
	for _, o in ipairs(Origins.List) do
		local dot = new("Frame", { Parent = map, BorderSizePixel = 0, BackgroundColor3 = C.goldDim, AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(o.Map.X, o.Map.Y), Size = UDim2.fromOffset(10, 10) }, { corner(8), stroke(C.inset, 2) })
		local name = label({ Parent = map, Text = o.Homeland, TextSize = 11, TextColor3 = C.muted, TextXAlignment = Enum.TextXAlignment.Center,
			AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(o.Map.X, 0, o.Map.Y, -9), Size = UDim2.fromOffset(130, 12) })
		markers[o.Id] = { dot = dot, name = name }
	end
	local originName = label({ Parent = originCard, Text = "", Font = TITLE, TextSize = 28, TextColor3 = C.gold,
		Position = UDim2.fromOffset(18, 196), Size = UDim2.fromOffset(300, 34) })
	local originStory = label({ Parent = originCard, Text = "", TextSize = 15, TextWrapped = true,
		TextYAlignment = Enum.TextYAlignment.Top, Position = UDim2.fromOffset(18, 232), Size = UDim2.fromOffset(302, 80) })
	local originStart = factRow(originCard, 322, "You wake at", "")
	local originUp = factRow(originCard, 348, "Trusted by", "")
	local originDown = factRow(originCard, 374, "Wary of you", "")
	local originItem = factRow(originCard, 400, "You carry", "")
	originUp.TextColor3, originDown.TextColor3 = C.good, C.bad
	label({ Parent = originCard, Text = "You still choose whom to serve at the end of Chapter 2.", TextSize = 13, TextColor3 = C.muted,
		TextWrapped = true, Position = UDim2.fromOffset(18, 440), Size = UDim2.fromOffset(302, 40) })
	table.insert(refreshers, function()
		local o = Origins.Find(choice.origin)
		originName.Text = o.Name
		originStory.Text = o.Story
		originStart.Text = o.Start
		originUp.Text = o.Standing.Up
		originDown.Text = o.Standing.Down or "No one"
		originItem.Text = o.Item
		for id, m in pairs(markers) do
			local on = id == choice.origin
			m.dot.BackgroundColor3 = if on then C.gold else C.goldDim
			m.dot.Size = if on then UDim2.fromOffset(16, 16) else UDim2.fromOffset(10, 10)
			m.name.TextColor3 = if on then C.text else C.muted
		end
	end)

	-- Traits step -----------------------------------------------------------------------------------------------
	local traitLeft = own("traits", panel({ Name = "TraitList", Parent = root, Position = UDim2.fromOffset(0, 84), Size = UDim2.fromOffset(250, 576) }))
	sectionTitle(traitLeft, "Traits", 16, 12)
	local traitCard = own("traits", panel({ Name = "TraitCard", Parent = root, Position = UDim2.fromOffset(782, 84), Size = UDim2.fromOffset(338, 500) }))
	local function traitBlock(y: number)
		local title = label({ Parent = traitCard, Text = "", Font = TITLE, TextSize = 24, TextColor3 = C.gold,
			Position = UDim2.fromOffset(18, y), Size = UDim2.fromOffset(300, 30) })
		local up = label({ Parent = traitCard, Text = "", TextSize = 15, TextColor3 = C.good, TextWrapped = true,
			TextYAlignment = Enum.TextYAlignment.Top, Position = UDim2.fromOffset(18, y + 32), Size = UDim2.fromOffset(302, 36) })
		local down = label({ Parent = traitCard, Text = "", TextSize = 15, TextColor3 = C.bad, TextWrapped = true,
			TextYAlignment = Enum.TextYAlignment.Top, Position = UDim2.fromOffset(18, y + 68), Size = UDim2.fromOffset(302, 36) })
		return function(trait)
			title.Text = if trait then trait.Name else "Pick a trait"
			title.TextColor3 = if trait then C.gold else C.muted
			up.Text = if trait then "+  " .. trait.Up[3] else ""
			down.Text = if trait then "-  " .. trait.Down[3] else ""
		end
	end
	sectionTitle(traitCard, "Your traits", 18, 14)
	local shows = { traitBlock(38), traitBlock(150) }
	sectionTitle(traitCard, "Looking at", 18, 272)
	local showHover = traitBlock(296)
	local traitCount = label({ Parent = traitCard, Text = "", Font = BOLD, TextSize = 14, TextColor3 = C.muted,
		TextXAlignment = Enum.TextXAlignment.Right, Position = UDim2.fromOffset(180, 14), Size = UDim2.fromOffset(140, 18) })
	pickList(traitLeft, Traits.List, {
		prefix = "Trait_", top = 34, step = 33.5, height = 30, titleSize = 17,
		isOn = function(t)
			return table.find(choice.traits, t.Id) ~= nil
		end,
		onPick = function(t)
			local at = table.find(choice.traits, t.Id)
			if at then
				table.remove(choice.traits, at)
			elseif #choice.traits < Traits.Pick then
				table.insert(choice.traits, t.Id)
			else -- full: the newest pick replaces the older one
				table.remove(choice.traits, 1)
				table.insert(choice.traits, t.Id)
			end
		end,
		onHover = function(t)
			showHover(t)
		end,
	})
	showHover(nil)
	table.insert(refreshers, function()
		for i, show in ipairs(shows) do
			show(Traits.Find(choice.traits[i]))
		end
		traitCount.Text = #choice.traits .. " / " .. Traits.Pick
	end)

	-- Back / Next (first time) or Cancel / Save (reopened) ------------------------------------------------------
	local confirm = button({ Name = "Confirm", Parent = root, Text = "", Font = TITLE, TextSize = 26,
		Position = UDim2.fromOffset(958, 598), Size = UDim2.fromOffset(162, 62) }, "gold")
	local back = button({ Name = if firstTime then "Back" else "Cancel", Parent = root, Text = if firstTime then "Back" else "Cancel",
		TextSize = 18, Position = UDim2.fromOffset(782, 598), Size = UDim2.fromOffset(162, 62) })
	local before = table.clone(look)
	local beforeClass = choice.class

	local function showStep(i: number)
		step = i
		local id = STEPS[i][1]
		for stepId, list in pairs(stepPanels) do
			for _, inst in ipairs(list) do
				(inst :: GuiObject).Visible = stepId == id
			end
		end
		for k, tab in ipairs(stepTabs) do
			tab:SetAttribute("Selected", k == i)
			tab:FindFirstChildOfClass("UIStroke").Color = if k == i then C.gold else C.edge
			tab.TextColor3 = if k == i then C.gold else C.text
		end
		subtitle.Text = HINTS[id]
		if firstTime then
			back.Visible = i > 1
			confirm.Text = if i < #STEPS then "Next" else "Begin"
		else
			confirm.Text = "Save"
		end
		refresh()
	end
	for i, tab in ipairs(stepTabs) do
		tab.MouseButton1Click:Connect(function()
			showStep(i)
		end)
	end
	table.insert(refreshers, function() -- Begin needs both traits
		local ready = not firstTime or step < #STEPS or #choice.traits == Traits.Pick
		confirm.BackgroundTransparency = if ready then 0 else 0.6
		confirm.TextTransparency = if ready then 0 else 0.4
	end)

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
		local hairData = HairLayer.For(art, look.style)
		HairLayer.Show(hairSprite, hairData, hairData and Recolour.GetHair(art, look) or nil, useAnim, direction, frame, art.Cell)
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
			remote:FireServer({ look = Appearance.Encode(look), class = choice.class, origin = choice.origin,
				traits = table.clone(choice.traits) })
		else
			look, choice.class = before, beforeClass
		end
	end
	confirm.MouseButton1Click:Connect(function()
		if firstTime and step < #STEPS then
			showStep(step + 1)
		elseif not firstTime or #choice.traits == Traits.Pick then
			close(true)
		end
	end)
	back.MouseButton1Click:Connect(function()
		if firstTime then
			showStep(math.max(1, step - 1))
		else
			close(false)
		end
	end)

	holdStill(true)
	gui = screen
	showStep(1)
	setLook(look)
end

local function open(firstTime: boolean)
	if gui then
		return
	end
	look = Appearance.Decode(player:GetAttribute("Appearance"))
	local saved = Profile.Sanitize({ class = player:GetAttribute("Class"), origin = player:GetAttribute("Origin"),
		traits = Profile.DecodeTraits(player:GetAttribute("Traits")) })
	choice = { class = saved.class, origin = saved.origin, traits = saved.traits }
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
