-- Placeholder hero drawn in code: 12 x 20 sprite pixels, 3 drawn sheets (S, N, E; West = East mirrored).
-- Same art contract as a sheet manifest (Kind, Pivot, StudsPerPixel, Anims), so either can be swapped in.
local HeroSprite = {}

HeroSprite.Kind = "Rows"
HeroSprite.Width = 12
HeroSprite.Height = 20
HeroSprite.Pivot = Vector2.new(6, 20) -- feet: bottom centre, px from the top-left
HeroSprite.StudsPerPixel = 0.25 -- 20 px = 5 studs
HeroSprite.Anims = {
	idle = { Frames = 1, FPS = 1, Mode = "Loop" },
	run = { Frames = 2, FPS = 8, Mode = "Loop" },
}
HeroSprite.Palette = {
	h = Color3.fromRGB(60, 40, 30), -- hair
	s = Color3.fromRGB(235, 190, 150), -- skin
	e = Color3.fromRGB(30, 30, 40), -- eyes
	c = Color3.fromRGB(40, 70, 140), -- cloak (Varrow lapis)
	a = Color3.fromRGB(170, 175, 185), -- armour
	l = Color3.fromRGB(70, 60, 55), -- legs
	b = Color3.fromRGB(45, 35, 30), -- boots
	w = Color3.fromRGB(210, 215, 225), -- sword
}

local BLANK = "............"

-- Rows 1-14: head and torso.
local BODY = {
	S = {
		"....hhhh....",
		"...hhhhhh...",
		"...hssssh...",
		"...sesses...",
		"...ssssss...",
		"....ssss....",
		"..cccccccc..",
		".cccaaaaccc.",
		".ccaaaaaacc.",
		".scaaaaaacs.",
		".scaaaaaacs.",
		".s.aaaaaa.s.",
		"...cccccc...",
		"...cccccc...",
	},
	N = {
		"....hhhh....",
		"...hhhhhh...",
		"...hhhhhh...",
		"...hhhhhh...",
		"...hhhhhh...",
		"....ssss....",
		"..cccccccc..",
		".cccccccccc.",
		".cccccccccc.",
		".sccccccccs.",
		".sccccccccs.",
		"..cccccccc..",
		"...cccccc...",
		"...cccccc...",
	},
	E = {
		".....hhhh...",
		"....hhhhhh..",
		"....hhssss..",
		"....hhsses..",
		"....hsssss..",
		".....sss....",
		"....cccccc..",
		"...cccaaaa..",
		"...ccaaaaas.",
		"...ccaaaaasw",
		"...ccaaaaa.w",
		"...cccaaaa.w",
		"....cccccc.w",
		"....cccccc..",
	},
}

-- Rows 15-19: legs per pose.
local FRONT_LEGS = {
	Idle = { "...ll..ll...", "...ll..ll...", "...ll..ll...", "...bb..bb...", "..bbb..bbb.." },
	RunA = { "...ll...ll..", "..ll....ll..", "..ll.....ll.", "..bb.....bb.", ".bbb.....bbb" },
	RunB = { "....llll....", "....llll....", "....ll.ll...", "....bb.bb...", "...bbb.bbb.." },
}

local LEGS = {
	S = FRONT_LEGS,
	N = FRONT_LEGS,
	E = {
		Idle = { "....ll.ll...", "....ll.ll...", "....ll.ll...", "....bb.bbb..", "...bbb.bbb.." },
		RunA = { "....ll..ll..", "...ll....ll.", "..ll.....ll.", "..bb.....bbb", ".bbb........" },
		RunB = { "....llll....", "....llll....", ".....ll.....", ".....bbb....", "....bbbb...." },
	},
}

-- Which drawn sheet stands in for each of the eight facings, and whether it is mirrored.
local SHEET_FOR = {
	S = { "S", false }, SW = { "S", false }, SE = { "S", false },
	N = { "N", false }, NW = { "N", false }, NE = { "N", false },
	E = { "E", false }, W = { "E", true },
}

-- Returns the frame's rows and whether to mirror them.
function HeroSprite.Draw(direction: string, anim: string, frame: number): ({ string }, boolean)
	local sheet, mirror = table.unpack(SHEET_FOR[direction])
	local pose = if anim == "run" then (if frame == 1 then "RunA" else "RunB") else "Idle"
	local rows = table.clone(BODY[sheet])
	for _, row in ipairs(LEGS[sheet][pose]) do
		table.insert(rows, row)
	end
	table.insert(rows, BLANK)
	return rows, mirror
end

return HeroSprite
