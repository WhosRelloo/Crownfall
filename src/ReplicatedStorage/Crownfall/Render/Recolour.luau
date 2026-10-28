-- Repaints sprite images with a player's look and bakes them into static content (client only).
-- Each image is read into an EditableImage, painted class by class (Shared/Appearance), baked with
-- AssetService:CreateDataModelContentAsync so it no longer counts against the editable-memory budget, then freed.
-- Each source image is downloaded once and its pixels kept, so later looks only repaint and bake (~15 ms each).
-- Jobs run from a queue, a few at a time; Get never yields and returns nil until its image is ready.
local AssetService = game:GetService("AssetService")
local RS = game:GetService("ReplicatedStorage")

local Appearance = require(RS.Crownfall.Shared.Appearance)
local ClassMap = require(script.Parent.ClassMap)
local HairLayer = require(script.Parent.HairLayer)
local SheetMath = require(script.Parent.SheetMath)

local Recolour = {}

local baked = {} -- [key] = Content
local queued = {} -- [key] = true while waiting or baking
local queue = {} -- jobs, next first
local classCache = {} -- [rig/anim/direction] = class buffer
local sources = {} -- [asset id] = { pixels = buffer, size = Vector2 } once downloaded, or { waiting = {threads} }
local WORKERS = 3 -- downloads in flight at once
local workers = 0
local broken = false -- the Editable APIs failed once: stop trying, show drawn colours
local ready = Instance.new("BindableEvent")
Recolour.Ready = ready.Event -- fires (key) after an image is baked

-- The image an anim/direction reads from, and the key its class map and bakes are stored under.
local function source(art, anim: string, direction: string): (string?, string)
	local def = art.Anims[anim]
	local id = SheetMath.Image(def, direction)
	if id then
		return id, anim .. "/" .. direction
	end
	return art.Layers.full[art.Outfit][anim], anim
end

local function mapsFor(art)
	local folder = script.Parent:FindFirstChild("ClassMaps")
	local module = folder and folder:FindFirstChild(art.Rig)
	return module and require(module)
end

local function classesFor(art, anim: string, strip: string, pixels: buffer, size: Vector2, text: string?): buffer
	local key = art.Rig .. "/" .. strip
	local found = classCache[key]
	if found then
		return found
	end
	if text then -- a hair atlas carries its own map
		found = ClassMap.Decode(text, size.X, size.Y)
		classCache[key] = found
		return found
	end
	local maps = mapsFor(art)
	local direction = string.match(strip, "/(%a+)$")
	local text = maps and maps.Anims[anim] and direction and maps.Anims[anim][direction]
	found = if text
		then ClassMap.Decode(text, size.X, size.Y)
		else ClassMap.ClassifyUpright(pixels, size.X, size.Y, art.Cell)
	classCache[key] = found
	return found
end

local function paint(pixels: buffer, classes: buffer, count: number, ramps, ranges)
	local memo = {} -- [class * 2^24 + rgb] = new rgb: sheets reuse few colours
	for p = 0, count - 1 do
		local class = buffer.readu8(classes, p)
		if not ramps[class] then
			continue
		end
		local i = p * 4
		if buffer.readu8(pixels, i + 3) == 0 then
			continue
		end
		local r, g, b = buffer.readu8(pixels, i), buffer.readu8(pixels, i + 1), buffer.readu8(pixels, i + 2)
		local k = class * 16777216 + r * 65536 + g * 256 + b
		local new = memo[k]
		if not new then
			local nr, ng, nb = Appearance.RecolourPixel(r, g, b, class, ramps, ranges)
			new = nr * 65536 + ng * 256 + nb
			memo[k] = new
		end
		buffer.writeu8(pixels, i, new // 65536)
		buffer.writeu8(pixels, i + 1, (new // 256) % 256)
		buffer.writeu8(pixels, i + 2, new % 256)
	end
end

-- The drawn pixels of an image, downloaded once (concurrent askers wait for the same download).
local function sourceFor(id: string)
	local entry = sources[id]
	if entry and entry.pixels then
		return entry
	end
	if entry then
		table.insert(entry.waiting, coroutine.running())
		coroutine.yield()
		return sources[id]
	end
	entry = { waiting = {} }
	sources[id] = entry
	local ok, result = pcall(function()
		local image = AssetService:CreateEditableImageAsync(Content.fromUri(id))
		local size = image.Size
		local pixels = image:ReadPixelsBuffer(Vector2.zero, size)
		image:Destroy()
		return { pixels = pixels, size = size }
	end)
	sources[id] = if ok then result else nil
	for _, thread in ipairs(entry.waiting) do
		task.spawn(thread)
	end
	if not ok then
		error(result, 0)
	end
	return result
end

local function bake(job)
	local source = sourceFor(job.id)
	if not source then
		error("could not load " .. job.id, 0)
	end
	local size = source.size
	local pixels = buffer.create(buffer.len(source.pixels))
	buffer.copy(pixels, 0, source.pixels)
	local image = AssetService:CreateEditableImage({ Size = size })
	local ok, err = pcall(function()
		local classes = classesFor(job.art, job.anim, job.strip, pixels, size, job.classes)
		local maps = mapsFor(job.art)
		local ranges = Appearance.RangesByClass(maps.Ranges)
		paint(pixels, classes, size.X * size.Y, Appearance.Ramps(job.look), ranges)
		image:WritePixelsBuffer(Vector2.zero, size, pixels)
		local result, content = AssetService:CreateDataModelContentAsync(Content.fromObject(image))
		assert(result == Enum.CreateContentResult.Success, "bake failed: " .. tostring(result))
		baked[job.key] = content
	end)
	image:Destroy()
	if not ok then
		error(err, 0)
	end
end

local function work()
	while workers < WORKERS and #queue > 0 do
		workers += 1
		task.spawn(function()
			while #queue > 0 and not broken do
				local job = table.remove(queue, 1)
				local ok, err = pcall(bake, job)
				queued[job.key] = nil
				if ok then
					ready:Fire(job.key)
				elseif not broken then
					broken = true
					warn("[Crownfall] recolour off, showing drawn colours: " .. tostring(err))
				end
				task.wait()
			end
			if broken then
				table.clear(queue)
				table.clear(queued)
			end
			workers -= 1
		end)
	end
end

local function enqueue(art, look, anim: string, direction: string, urgent: boolean): string?
	local id, strip = source(art, anim, direction)
	if not id then
		return nil
	end
	local key = art.Rig .. "|" .. Appearance.Encode(look) .. "|" .. strip
	if baked[key] or broken then
		return key
	end
	if queued[key] then
		if urgent then -- move it to the front
			for i, job in ipairs(queue) do
				if job.key == key then
					table.insert(queue, 1, table.remove(queue, i))
					break
				end
			end
		end
		return key
	end
	queued[key] = true
	local job = { key = key, id = id, art = art, look = look, anim = anim, strip = strip }
	if urgent then
		table.insert(queue, 1, job)
	else
		table.insert(queue, job)
	end
	work()
	return key
end

-- The baked image for this frame's strip, or nil while it bakes (show the drawn image meanwhile) or when the look
-- is as drawn. Asking queues it at the front.
function Recolour.Get(art, look, anim: string, direction: string)
	if Appearance.IsDrawn(look) or not mapsFor(art) then
		return nil
	end
	local key = enqueue(art, look, anim, direction, true)
	return key and baked[key]
end

local function enqueueHair(art, look, urgent: boolean): string?
	local data = HairLayer.For(art, look.style)
	if not data then
		return nil
	end
	local strip = "hair:" .. data.Id
	local key = art.Rig .. "|" .. Appearance.Encode(look) .. "|" .. strip
	if baked[key] or broken or queued[key] then
		return key
	end
	queued[key] = true
	local job = { key = key, id = data.Image, art = art, look = look, anim = "hair", strip = strip, classes = data.Classes }
	if urgent then
		table.insert(queue, 1, job)
	else
		table.insert(queue, job)
	end
	work()
	return key
end

-- The look's hairstyle atlas repainted with its hair colour, or nil while it bakes / when nothing needs painting.
function Recolour.GetHair(art, look)
	if Appearance.IsDrawn(look) or not mapsFor(art) then
		return nil
	end
	local key = enqueueHair(art, look, true)
	return key and baked[key]
end

-- Queues every animation in every direction for a look, so they are ready before they are first shown.
function Recolour.Prepare(art, look)
	if Appearance.IsDrawn(look) or not mapsFor(art) then
		return
	end
	for anim, def in pairs(art.Anims) do
		if def.Images then
			for direction in pairs(def.Images) do
				enqueue(art, look, anim, direction, false)
			end
		else
			enqueue(art, look, anim, "S", false)
		end
	end
	enqueueHair(art, look, false)
end

-- True once every image of a look is baked (or recolouring is off).
function Recolour.IsReady(art, look): boolean
	if broken or Appearance.IsDrawn(look) or not mapsFor(art) then
		return true
	end
	for anim, def in pairs(art.Anims) do
		for direction in pairs(def.Images or { S = true }) do
			local _, strip = source(art, anim, direction)
			if not baked[art.Rig .. "|" .. Appearance.Encode(look) .. "|" .. strip] then
				return false
			end
		end
	end
	local hair = HairLayer.For(art, look.style)
	return hair == nil or baked[art.Rig .. "|" .. Appearance.Encode(look) .. "|hair:" .. hair.Id] ~= nil
end

return Recolour
