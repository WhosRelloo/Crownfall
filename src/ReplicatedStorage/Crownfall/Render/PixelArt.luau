-- Turns rows of palette letters into horizontal runs, so a sprite draws as few Frames as possible.
-- "." is an empty pixel. Returned x and y are 0-based; mirror flips left and right.
local PixelArt = {}

function PixelArt.ToRuns(rows: { string }, mirror: boolean?): { { x: number, y: number, w: number, key: string } }
	local runs = {}
	local width = #rows[1]
	for y, row in ipairs(rows) do
		assert(#row == width, ("row %d is %d wide, expected %d"):format(y, #row, width))
		local x = 1
		while x <= width do
			local key = row:sub(x, x)
			local stop = x
			while stop < width and row:sub(stop + 1, stop + 1) == key do
				stop += 1
			end
			if key ~= "." then
				local left = if mirror then width - stop else x - 1
				table.insert(runs, { x = left, y = y - 1, w = stop - x + 1, key = key })
			end
			x = stop + 1
		end
	end
	return runs
end

return PixelArt
