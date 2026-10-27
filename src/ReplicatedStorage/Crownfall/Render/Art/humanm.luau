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
	},
	Layers = {
		full = {
			rags = {
				idle = "rbxassetid://120091824682648",
			},
		},
	},
}
