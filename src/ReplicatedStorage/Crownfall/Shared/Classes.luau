-- Starting classes (Docs/Plans/2026-10-28-class-origin-traits-hair.md, section 2). A class is a starting kit and
-- role, not a lock: it can be switched at any shrine (blueprint 5). Weapon art beyond the longsword arrives with
-- combat; until then every class is drawn holding the longsword.
local Classes = {}

Classes.List = {
	{
		Id = "duelist",
		Name = "Duelist",
		Weapon = "Longsword",
		Armour = "Medium",
		Power = "Oath Riposte",
		Discipline = "Striker",
		Role = "Balanced blade work. Wins the exchange by reading tells and parrying.",
	},
	{
		Id = "vanguard",
		Name = "Vanguard",
		Weapon = "Sword & Shield",
		Armour = "Heavy",
		Power = "Rallying Cry",
		Discipline = "Vanguard",
		Role = "The wall. Best block and widest parry; draws attention and keeps allies standing.",
	},
	{
		Id = "lancer",
		Name = "Lancer",
		Weapon = "Spear",
		Armour = "Medium",
		Power = "Thrust Deflect",
		Discipline = "Vanguard",
		Role = "Owns the space in front of them. Sweeps groups, answers thrusts, strongest in the saddle.",
	},
	{
		Id = "breaker",
		Name = "Breaker",
		Weapon = "Greatblade",
		Armour = "Heavy",
		Power = "Sundering Blow",
		Discipline = "Breaker",
		Role = "Slow and crushing. Trades blows through heavy swings to shatter posture.",
	},
	{
		Id = "striker",
		Name = "Striker",
		Weapon = "Twin Fangs",
		Armour = "Light",
		Power = "Cinder Edge",
		Discipline = "Striker",
		Role = "Fast and evasive. Bleeds enemies, strikes from behind, never stands still.",
	},
	{
		Id = "warder",
		Name = "Warder",
		Weapon = "Lantern Catalyst",
		Armour = "Light",
		Power = "Lantern Ward",
		Discipline = "Warder",
		Role = "Casts and shields. Cleanses allies, parries with a ward pulse, can still duel.",
	},
}

Classes.Default = "duelist"

function Classes.Find(id: any)
	for _, class in ipairs(Classes.List) do
		if class.Id == id then
			return class
		end
	end
	return nil
end

return Classes
