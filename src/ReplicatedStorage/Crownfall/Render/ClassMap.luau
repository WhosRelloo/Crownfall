-- Colour-class maps: which pixels of a sheet are skin, hair, outfit and so on (Tools/colour_classes.py).
local ClassMap = {}

local LETTER = { a = 0, b = 1, c = 2, d = 3, e = 4, f = 5, g = 6 }

-- Expands a run-length string from Tools/class_maps.py ("a12c3e") into one byte per pixel (w * h, row-major).
function ClassMap.Decode(text: string, w: number, h: number): buffer
	local out = buffer.create(w * h)
	local at = 0
	for letter, count in string.gmatch(text, "(%a)(%d*)") do
		local n = if count == "" then 1 else tonumber(count) :: number
		buffer.fill(out, at, LETTER[letter], n)
		at += n
	end
	assert(at == w * h, string.format("class map has %d pixels, expected %d", at, w * h))
	return out
end

-- Bands of an upright figure as fractions of its height from the top of the head, measured on the walk drawings
-- (Tools/colour_classes.py: hair down to the hair line + 5 rows, face and neck skin to + 12, hips at row 66).
local HAIR_BAND, HIP_BAND = 0.22, 0.63
local BOOT_ROWS = 14
local OUTLINE_LUM, STEEL_SAT = 16, 0.18

local function hsv(r: number, g: number, b: number): (number, number, number)
	local h, s, v = Color3.fromRGB(r, g, b):ToHSV()
	return h, s, v
end

-- For sheets with no stored map (the idle): classifies each cell of a pixel buffer from colour and height alone.
-- Fine for a figure standing upright; animations that bend or roll use the stored maps.
function ClassMap.ClassifyUpright(pixels: buffer, w: number, h: number, cell: number): buffer
	local out = buffer.create(w * h)
	for cy = 0, h // cell - 1 do
		for cx = 0, w // cell - 1 do
			local top, bottom = nil, nil
			for y = 0, cell - 1 do
				for x = 0, cell - 1 do
					local i = ((cy * cell + y) * w + cx * cell + x) * 4
					if buffer.readu8(pixels, i + 3) > 0 then
						top = top or y
						bottom = y
						break
					end
				end
			end
			if not top then
				continue
			end
			local height = bottom - top + 1
			for y = top, bottom do
				local rel = (y - top) / height
				for x = 0, cell - 1 do
					local p = (cy * cell + y) * w + cx * cell + x
					local i = p * 4
					if buffer.readu8(pixels, i + 3) == 0 then
						continue
					end
					local r, g, b = buffer.readu8(pixels, i), buffer.readu8(pixels, i + 1), buffer.readu8(pixels, i + 2)
					local lum = 0.3 * r + 0.59 * g + 0.11 * b
					local hue, sat = hsv(r, g, b)
					local class
					if lum < OUTLINE_LUM then
						class = 1
					elseif sat < STEEL_SAT and lum > 28 then
						class = 2
					elseif hue >= 0.02 and hue <= 0.11 and sat > 0.35 and lum > 70 and rel < HIP_BAND then
						class = 3
					elseif rel < HAIR_BAND then
						class = 4
					elseif y > bottom - BOOT_ROWS and sat > 0.45 then
						class = 6
					else
						class = 5
					end
					buffer.writeu8(out, p, class)
				end
			end
		end
	end
	return out
end

return ClassMap
