-- Origins: the kingdom a player comes from and spawns in (Docs/Plans/2026-10-28-class-origin-traits-hair.md,
-- section 3; blueprint 5.2). Sets the start, early standing and a starting item; the real pledge comes in Chapter 2.
-- Map: the homeland's place on the creator's map of the Reach (0-1 across, 0-1 down; north is up).
-- Spawn: default start (root position), used when workspace.CrownfallOriginSpawns has no part with the origin's id.
-- The place has a coloured placeholder pad per origin at these spots; move the pads to move the starts.
local Origins = {}

Origins.List = {
	{
		Id = "varrow",
		Name = "Varrow Squire",
		Homeland = "Crown of Varrow",
		Start = "Highland garrison",
		Standing = { Up = "Crown of Varrow", Down = "The Thornborn" },
		Item = "Squire's signet",
		Story = "Raised on drill yards and old imperial oaths. Knights trust you; the forest clans remember what Varrow did.",
		Map = Vector2.new(0.5, 0.22),
		Spawn = Vector3.new(0, 3, -40),
	},
	{
		Id = "compact",
		Name = "Compact Caravaneer",
		Homeland = "The Ashen Compact",
		Start = "Salt-road convoy",
		Standing = { Up = "The Ashen Compact", Down = "Crown of Varrow" },
		Item = "Trade map of the Ashmarch",
		Story = "You grew up between wagon wheels. Merchants give you better first prices and the road's gossip finds you first.",
		Map = Vector2.new(0.55, 0.78),
		Spawn = Vector3.new(0, 3, 40),
	},
	{
		Id = "lantern",
		Name = "Lantern Novice",
		Homeland = "Order of the Quiet Lantern",
		Start = "Abbey infirmary",
		Standing = { Up = "Order of the Quiet Lantern", Down = "The Hollow Choir" },
		Item = "Novice's lantern charm",
		Story = "You tended the blighted in a cliffside abbey. You can read Shard script, and sickness holds fewer secrets.",
		Map = Vector2.new(0.8, 0.38),
		Spawn = Vector3.new(40, 3, 0),
	},
	{
		Id = "thornborn",
		Name = "Thornborn Exile",
		Homeland = "The Thornborn",
		Start = "Forest-edge camp",
		Standing = { Up = "The Thornborn", Down = "Crown of Varrow" },
		Item = "Antler fetish",
		Story = "Cast out, but never cut off. The clans open their paths to you early; Varrow's guards keep a hand on their hilts.",
		Map = Vector2.new(0.2, 0.42),
		Spawn = Vector3.new(-40, 3, 0),
	},
	{
		Id = "roadborn",
		Name = "Roadborn Orphan",
		Homeland = "The Roadwardens",
		Start = "Waystation",
		Standing = { Up = "The Roadwardens" },
		Item = "Courier's satchel",
		Story = "Raised by the keepers of the Old Roads. Owed to no crown, fast over rooftops, and the Couriers' Guild knows your name.",
		Map = Vector2.new(0.45, 0.52),
		Spawn = Vector3.new(0, 3, 18),
	},
}

Origins.Default = "roadborn"

function Origins.Find(id: any)
	for _, origin in ipairs(Origins.List) do
		if origin.Id == id then
			return origin
		end
	end
	return nil
end

return Origins
