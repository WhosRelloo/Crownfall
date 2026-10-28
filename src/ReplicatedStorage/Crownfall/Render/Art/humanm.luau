-- Art manifest: male human, Phase 1 flattened sheets (Docs/Art-Spec.md section 10).
-- IDs come from Art/Sprites/asset-ids.json. Animations without a sheet yet fall back to idle.
return {
	Kind = "Sheet",
	Rig = "humanm",
	Outfit = "rags",
	Cell = 96, -- px
	Pivot = Vector2.new(48, 88), -- standard feet point, px from the cell's top-left
	StudsPerPixel = 5 / 64, -- 64 px character = 5 studs
	Anims = {
		-- Uploaded 2026-10-27: 2 directions per 768 px row, feet on row 79, feet x varies per direction.
		idle = {
			Frames = 4,
			FPS = 6,
			Mode = "Loop",
			SheetSize = Vector2.new(768, 384),
			Layout = { S = { 0, 0 }, SE = { 0, 4 }, E = { 1, 0 }, SW = { 1, 4 }, NE = { 2, 0 }, N = { 2, 4 }, NW = { 3, 0 }, W = { 3, 4 } },
			Pivot = Vector2.new(48, 80),
			FeetX = { S = 48, SE = 43, E = 42, SW = 52, NE = 45, N = 44, NW = 48, W = 54 },
		},
		-- Uploaded 2026-10-27 (walk 7:23 PM, run 7:17 PM) as one 8-frame strip (768 x 96) per direction;
		-- feet on the standard pivot. Each checked in Studio: pixel count and centre match the sheets.
		walk = {
			Frames = 8,
			FPS = 10,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://106484660819753",
				SW = "rbxassetid://96559634052373",
				W = "rbxassetid://110243873048154",
				NW = "rbxassetid://109047176703791",
				N = "rbxassetid://129131814406601",
				NE = "rbxassetid://131717595196711",
				E = "rbxassetid://78807560011840",
				SE = "rbxassetid://75239989873965",
			},
		},
		run = {
			Frames = 8,
			FPS = 12,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://72152421354623",
				SW = "rbxassetid://90521609780488",
				W = "rbxassetid://104929602934605",
				NW = "rbxassetid://79950080640854",
				N = "rbxassetid://114419397061647",
				NE = "rbxassetid://74761754773042",
				E = "rbxassetid://92192337548778",
				SE = "rbxassetid://111637685606463",
			},
		},
		-- Uploaded 2026-10-27 6:47 PM; IDs matched to directions by pixel count and centre in Studio.
		dodge = {
			Frames = 8,
			FPS = 20,
			Mode = "Once",
			Images = {
				S = "rbxassetid://136076529892246",
				SW = "rbxassetid://140550640499414",
				W = "rbxassetid://90974670581621",
				NW = "rbxassetid://102124577126013",
				N = "rbxassetid://140511944308809",
				NE = "rbxassetid://101463775209688",
				E = "rbxassetid://132207485689053",
				SE = "rbxassetid://133299446146726",
			},
		},
	},
	Layers = {
		full = {
			rags = {
				idle = "rbxassetid://120091824682648",
			},
		},
	},
}
