local RS = game:GetService("ReplicatedStorage")
local Render = RS.Crownfall.Render -- dot access errors at once if the folder is missing (WaitForChild would hang)
local CameraMath = require(Render.CameraMath)
local Facing = require(Render.Facing)
local PixelArt = require(Render.PixelArt)
local HeroSprite = require(Render.HeroSprite)
local SheetMath = require(Render.SheetMath)
local T = require(script.Parent.TestKit)

local spec = {}

spec["camera sits behind +Z and above the focus"] = function()
	local o = CameraMath.Offset(40, 70)
	T.near(o.X, 0)
	T.near(o.Y, math.sin(math.rad(40)) * 70)
	T.near(o.Z, math.cos(math.rad(40)) * 70)
end

spec["world motion maps to screen directions"] = function()
	local right = CameraMath.ToScreen(Vector3.new(1, 0, 0))
	T.near(right.X, 1)
	T.near(right.Y, 0)
	local away = CameraMath.ToScreen(Vector3.new(0, 0, -1))
	T.near(away.X, 0)
	T.near(away.Y, 1)
end

spec["facing picks one of eight directions"] = function()
	local function check(x, y, expected)
		T.eq(Facing.FromScreen(Vector2.new(x, y)), expected, ("(%d, %d)"):format(x, y))
	end
	check(0, 1, "N")
	check(1, 1, "NE")
	check(1, 0, "E")
	check(1, -1, "SE")
	check(0, -1, "S")
	check(-1, -1, "SW")
	check(-1, 0, "W")
	check(-1, 1, "NW")
	check(10, 1, "E") -- 84 degrees: still inside the E sector
end

spec["runs merge same-colour pixels and skip empty ones"] = function()
	local runs = PixelArt.ToRuns({ "aab.", ".bbb" })
	T.eq(#runs, 3)
	T.eq(runs[1].x, 0); T.eq(runs[1].w, 2); T.eq(runs[1].key, "a")
	T.eq(runs[2].x, 2); T.eq(runs[2].w, 1); T.eq(runs[2].key, "b")
	T.eq(runs[3].x, 1); T.eq(runs[3].y, 1); T.eq(runs[3].w, 3)
end

spec["mirror flips runs left to right"] = function()
	local runs = PixelArt.ToRuns({ "aa.." }, true)
	T.eq(runs[1].x, 2)
	T.eq(runs[1].w, 2)
end

spec["uneven rows are rejected"] = function()
	T.falsy(pcall(PixelArt.ToRuns, { "aaa", "aa" }))
end

spec["every placeholder frame is 12x20 and uses only palette colours"] = function()
	for _, dir in ipairs({ "S", "SW", "W", "NW", "N", "NE", "E", "SE" }) do
		for anim, def in pairs(HeroSprite.Anims) do
			for frame = 1, def.Frames do
				local rows = HeroSprite.Draw(dir, anim, frame)
				T.eq(#rows, HeroSprite.Height, ("%s/%s/%d rows"):format(dir, anim, frame))
				for i, row in ipairs(rows) do
					T.eq(#row, HeroSprite.Width, ("%s/%s/%d row %d width"):format(dir, anim, frame, i))
					for c in row:gmatch("[^%.]") do
						T.truthy(HeroSprite.Palette[c], ("%s/%s colour %q"):format(dir, anim, c))
					end
				end
			end
		end
	end
end

spec["placeholder mirrors the west side for east"] = function()
	local _, mirrorW = HeroSprite.Draw("W", "idle", 1)
	local _, mirrorE = HeroSprite.Draw("E", "idle", 1)
	T.eq(mirrorW, true)
	T.eq(mirrorE, false)
end

-- The uploaded idle sheet: 2 directions per row, feet on row 79, per-direction feet x.
local UPLOADED_IDLE = {
	Frames = 4,
	FPS = 6,
	Mode = "Loop",
	Layout = { S = { 0, 0 }, SE = { 0, 4 }, E = { 1, 0 }, SW = { 1, 4 }, NE = { 2, 0 }, N = { 2, 4 }, NW = { 3, 0 }, W = { 3, 4 } },
	Pivot = Vector2.new(48, 80),
	FeetX = { S = 48, SE = 43, E = 42, SW = 52, NE = 45, N = 44, NW = 48, W = 54 },
}

spec["layout sheets read the listed cell"] = function()
	local r = SheetMath.Rect(UPLOADED_IDLE, "SW", 2, 96, Vector2.new(48, 88))
	T.eq(r.Offset, Vector2.new(480, 96))
	T.eq(r.Size, Vector2.new(96, 96))
	T.eq(r.Pivot, Vector2.new(52, 80), "per-direction feet x and the sheet's own pivot y")
end

spec["standard 5-row sheets mirror the east side"] = function()
	local def = { Frames = 6, FPS = 8, Mode = "Loop", Rows = 5 }
	local w = SheetMath.Rect(def, "W", 1, 96, Vector2.new(48, 88))
	T.eq(w.Offset, Vector2.new(0, 192))
	T.eq(w.Size, Vector2.new(96, 96))
	local e = SheetMath.Rect(def, "E", 1, 96, Vector2.new(48, 88))
	T.eq(e.Offset, Vector2.new(96, 192), "starts at the right edge of the W frame")
	T.eq(e.Size, Vector2.new(-96, 96), "negative width draws it mirrored")
	local ne = SheetMath.Rect(def, "NE", 3, 96, Vector2.new(40, 88))
	T.eq(ne.Offset, Vector2.new(288, 288))
	T.eq(ne.Pivot, Vector2.new(56, 88), "mirrored feet x")
end

spec["standard 8-row sheets use every row"] = function()
	local def = { Frames = 4, FPS = 6, Mode = "Loop", Rows = 8 }
	local se = SheetMath.Rect(def, "SE", 1, 96, Vector2.new(48, 88))
	T.eq(se.Offset, Vector2.new(0, 672))
	T.eq(se.Size, Vector2.new(96, 96))
end

spec["frame timing loops, plays once and holds"] = function()
	local loop = { Frames = 4, FPS = 6, Mode = "Loop" }
	T.eq(SheetMath.FrameAt(loop, 0), 1)
	T.eq(SheetMath.FrameAt(loop, 0.5), 4)
	T.eq(SheetMath.FrameAt(loop, 0.7), 1)
	local once = { Frames = 4, FPS = 6, Mode = "Once" }
	T.eq(SheetMath.FrameAt(once, 5), 4)
	local hold = { Frames = 3, FPS = 12, Mode = "Hold" }
	T.eq(SheetMath.FrameAt(hold, 1), 3)
end

return spec
