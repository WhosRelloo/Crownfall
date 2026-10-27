-- Where a frame lives in a sprite sheet, and which frame plays at a given time (Docs/Art-Spec.md sections 2, 3, 10).
local SheetMath = {}

-- Standard row order. Rows 5-7 (east side) are optional: a 5-row sheet mirrors them from the west side.
local ROWS = { S = 0, SW = 1, W = 2, NW = 3, N = 4, NE = 5, E = 6, SE = 7 }
local MIRROR_OF = { NE = "NW", E = "W", SE = "SW" }

export type Rect = { Offset: Vector2, Size: Vector2, Pivot: Vector2 }

-- def: an anim entry from an art manifest. frame is 1-based. cell is the cell size in px.
-- Returns the ImageRectOffset / ImageRectSize to show and the feet pivot (px) in the frame as drawn on screen.
-- A negative Size.X draws the frame mirrored.
function SheetMath.Rect(def, direction: string, frame: number, cell: number, defaultPivot: Vector2): Rect
	local pivot = def.Pivot or defaultPivot
	local source, mirror = direction, false

	local row, col
	if def.Layout then
		if not def.Layout[source] and MIRROR_OF[source] then
			source, mirror = MIRROR_OF[source], true
		end
		local at = def.Layout[source]
		assert(at, "no layout cell for direction " .. direction)
		row, col = at[1], at[2]
	else
		if (def.Rows or 5) < 8 and MIRROR_OF[source] then
			source, mirror = MIRROR_OF[source], true
		end
		row, col = ROWS[source], 0
		assert(row, "unknown direction " .. tostring(direction))
	end

	local feetX = if def.FeetX and def.FeetX[source] then def.FeetX[source] else pivot.X
	local x, y = (col + frame - 1) * cell, row * cell
	if mirror then
		return { Offset = Vector2.new(x + cell, y), Size = Vector2.new(-cell, cell), Pivot = Vector2.new(cell - feetX, pivot.Y) }
	end
	return { Offset = Vector2.new(x, y), Size = Vector2.new(cell, cell), Pivot = Vector2.new(feetX, pivot.Y) }
end

-- 1-based frame to show `elapsed` seconds after the animation started.
function SheetMath.FrameAt(def, elapsed: number): number
	local step = math.floor(elapsed * def.FPS)
	if def.Mode == "Loop" then
		return step % def.Frames + 1
	end
	return math.min(step + 1, def.Frames)
end

return SheetMath
