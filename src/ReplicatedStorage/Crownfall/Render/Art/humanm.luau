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
		-- Uploaded 2026-10-27 as one 8-frame strip (768 x 96) per direction; feet on the standard pivot.
		walk = {
			Frames = 8,
			FPS = 10,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://78627164929550",
				SW = "rbxassetid://76736586081882",
				W = "rbxassetid://89173701039656",
				NW = "rbxassetid://140387225265342",
				N = "rbxassetid://130937814930740",
				NE = "rbxassetid://126049533991959",
				E = "rbxassetid://110635237754967",
				SE = "rbxassetid://82692421583733",
			},
		},
		run = {
			Frames = 8,
			FPS = 12,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://116626209923087",
				SW = "rbxassetid://107770828476982",
				W = "rbxassetid://132584542976980",
				NW = "rbxassetid://112155676937784",
				N = "rbxassetid://137030515857935",
				NE = "rbxassetid://136192886369643",
				E = "rbxassetid://87205627224690",
				SE = "rbxassetid://87188108632950",
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
