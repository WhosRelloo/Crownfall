-- Art manifest: female human (Tools/female.py), flattened sheets built by Tools/walk_cycle.py.
-- Uploaded 2026-10-27 (idle, walk, run 9:43 PM; dodge 9:46 PM) as one 8-frame strip (768 x 96) per direction,
-- feet on the standard pivot. Each ID checked in Studio against Art/Sprites/humanf pixel for pixel.
return {
	Kind = "Sheet",
	Rig = "humanf",
	Outfit = "rags",
	Cell = 96, -- px
	Pivot = Vector2.new(48, 88), -- standard feet point, px from the cell's top-left
	StudsPerPixel = 5 / 64, -- 64 px character = 5 studs
	Anims = {
		idle = {
			Frames = 8,
			FPS = 6,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://109138743202001",
				SW = "rbxassetid://108681677194709",
				W = "rbxassetid://123762127740509",
				NW = "rbxassetid://75904172438729",
				N = "rbxassetid://76455661190153",
				NE = "rbxassetid://137279476402385",
				E = "rbxassetid://95580869982546",
				SE = "rbxassetid://139411001313808",
			},
		},
		walk = {
			Frames = 8,
			FPS = 10,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://116323664671379",
				SW = "rbxassetid://88821136643211",
				W = "rbxassetid://131315862903425",
				NW = "rbxassetid://127838738695747",
				N = "rbxassetid://116047332671488",
				NE = "rbxassetid://87797069919674",
				E = "rbxassetid://79923080939514",
				SE = "rbxassetid://70862425963799",
			},
		},
		run = {
			Frames = 8,
			FPS = 12,
			Mode = "Loop",
			Images = {
				S = "rbxassetid://76340419541105",
				SW = "rbxassetid://97279637753016",
				W = "rbxassetid://140492383303263",
				NW = "rbxassetid://127170952751214",
				N = "rbxassetid://73189998652477",
				NE = "rbxassetid://80393141222405",
				E = "rbxassetid://86728325180069",
				SE = "rbxassetid://138639908732873",
			},
		},
		dodge = {
			Frames = 8,
			FPS = 20,
			Mode = "Once",
			Images = {
				S = "rbxassetid://135108887923888",
				SW = "rbxassetid://101822653054025",
				W = "rbxassetid://75690436634886",
				NW = "rbxassetid://90094014801751",
				N = "rbxassetid://135214794408679",
				NE = "rbxassetid://132914469528656",
				E = "rbxassetid://105802422892882",
				SE = "rbxassetid://90125549581840",
			},
		},
	},
	Layers = { full = { rags = {} } },
}
