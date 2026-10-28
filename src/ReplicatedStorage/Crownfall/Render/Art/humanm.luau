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
				S = "rbxassetid://75803123635354",
				SW = "rbxassetid://79061646861695",
				W = "rbxassetid://90353021831165",
				NW = "rbxassetid://101986689346199",
				N = "rbxassetid://121560794536755",
				NE = "rbxassetid://130912852757511",
				E = "rbxassetid://137310282059088",
				SE = "rbxassetid://91400436204682",
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
	},
	Layers = {
		full = {
			rags = {
				idle = "rbxassetid://120091824682648",
			},
		},
	},
}
