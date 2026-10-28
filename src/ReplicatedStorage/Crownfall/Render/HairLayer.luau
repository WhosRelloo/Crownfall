-- Hairstyle layers (Tools/hair_build.py, Tools/hair_wire.py): each hairstyle is one atlas image of every frame's hair,
-- drawn over the bald body. Render/Hair/<rig>_<style> holds the atlas id, size, frame rects and colour classes.
local HairLayer = {}

local ANIMS = { idle = 0, walk = 1, run = 2, dodge = 3 }
local ROWS = { S = 0, SW = 1, W = 2, NW = 3, N = 4, NE = 5, E = 6, SE = 7 }
local FRAMES = 8

local cache = {} -- [module] = parsed data

-- The hair data for a rig and hairstyle, or nil when that hairstyle isn't in the game yet.
function HairLayer.For(art, styleId: string?)
	local folder = script.Parent:FindFirstChild("Hair")
	local module = folder and styleId and folder:FindFirstChild(art.Rig .. "_" .. styleId)
	if not module then
		return nil
	end
	local data = cache[module]
	if not data then
		local raw = require(module)
		local rects = {}
		for entry in string.gmatch(raw.Rects, "[^;]+") do
			local v = string.split(entry, ",")
			table.insert(rects, { tonumber(v[1]), tonumber(v[2]), tonumber(v[3]), tonumber(v[4]), tonumber(v[5]), tonumber(v[6]) })
		end
		data = { Id = art.Rig .. "_" .. styleId, Image = raw.Image, Size = raw.Size, Rects = rects, Classes = raw.Classes }
		cache[module] = data
	end
	return data
end

-- { x, y, w, h, dx, dy } for a frame (1-based), or nil when the frame has no hair or the anim isn't in the atlas.
function HairLayer.Rect(data, anim: string, direction: string, frame: number)
	local a, r = ANIMS[anim], ROWS[direction]
	if not a or not r then
		return nil
	end
	local rect = data.Rects[(a * 8 + r) * FRAMES + frame]
	return if rect and rect[3] > 0 then rect else nil
end

-- Places an ImageLabel (sized in scale over a 96 px cell) to show this frame's hair; hides it when there is none.
function HairLayer.Show(label: ImageLabel, data, content: Content?, anim: string, direction: string, frame: number, cell: number)
	local rect = data and HairLayer.Rect(data, anim, direction, frame)
	if not rect then
		label.Visible = false
		return
	end
	label.Visible = true
	label.ImageContent = content or Content.fromUri(data.Image)
	label.ImageRectOffset = Vector2.new(rect[1], rect[2])
	label.ImageRectSize = Vector2.new(rect[3], rect[4])
	label.Position = UDim2.fromScale(rect[5] / cell, rect[6] / cell)
	label.Size = UDim2.fromScale(rect[3] / cell, rect[4] / cell)
end

return HairLayer
