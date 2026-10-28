-- Starter traits (Docs/Plans/2026-10-28-class-origin-traits-hair.md, section 4): pick 2 of 16 sidegrades.
-- Every trait moves exactly one stat for the better (Up) and one for the worse (Down), each by at most 25% of the
-- stat's base. Systems read a player's values through Traits.Value; stats of systems not built yet (shops, mounts,
-- ailments) are kept here so they apply as soon as those systems read them.
local Config = require(script.Parent.Config)

local Traits = {}

Traits.Pick = 2 -- traits chosen at creation

-- Stat registry: base value and which way is better. Bases come from Config where the system exists.
Traits.Stats = {
	DodgeCost = { Base = Config.Stamina.Costs.Dodge, Better = "lower", Unit = " stamina" },
	SprintCost = { Base = Config.Stamina.Costs.SprintPerSecond, Better = "lower", Unit = " stamina/s" },
	ClimbCost = { Base = Config.Stamina.Costs.ClimbPerSecond, Better = "lower", Unit = " stamina/s" },
	MaxStamina = { Base = Config.Stamina.Max, Better = "higher", Unit = "" },
	StaminaRegen = { Base = Config.Stamina.RegenPerSecond, Better = "higher", Unit = "/s" },
	RegenDelay = { Base = Config.Stamina.RegenDelay, Better = "lower", Unit = " s" },
	BlockPostureTaken = { Base = 1, Better = "lower", Unit = "x" },
	PostureDecay = { Base = Config.Posture.DecayPerSecond, Better = "higher", Unit = "/s" },
	PostureDecayDelay = { Base = Config.Posture.DecayDelay, Better = "lower", Unit = " s" },
	GuardBrokenTime = { Base = Config.Posture.BrokenTime.Player, Better = "lower", Unit = " s" },
	ParryWindow = { Base = Config.Parry.WindowFrames, Better = "higher", Unit = " frames" },
	LateParryWindow = { Base = Config.Parry.LateFrames, Better = "higher", Unit = " frames" },
	WhiffRecovery = { Base = Config.Parry.WhiffRecoveryFrames, Better = "lower", Unit = " frames" },
	DamageTaken = { Base = 1, Better = "lower", Unit = "x" },
	ResolveGain = { Base = 1, Better = "higher", Unit = "x" },
	PerfectParryResolve = { Base = 20, Better = "higher", Unit = "" }, -- blueprint 4.1
	ResolvePerHit = { Base = 3, Better = "higher", Unit = "" }, -- blueprint 4.1
	ResolveFade = { Base = 1, Better = "lower", Unit = "x" },
	GearWear = { Base = 1, Better = "lower", Unit = "x" },
	RepairCost = { Base = 1, Better = "lower", Unit = "x" },
	ShopPrices = { Base = 1, Better = "lower", Unit = "x" },
	QuestGold = { Base = 1, Better = "higher", Unit = "x" },
	AilmentBuildup = { Base = 1, Better = "lower", Unit = "x" },
	TonicHealing = { Base = 1, Better = "higher", Unit = "x" },
	MountBond = { Base = 1, Better = "higher", Unit = "x" },
	BanditNotice = { Base = 1, Better = "lower", Unit = "x" },
}

-- Up / Down: { Stat, Value } sets the stat to Value; Text is what the creator shows.
Traits.List = {
	{ Id = "light_footed", Name = "Light-footed",
		Up = { "DodgeCost", 22, "Dodge costs 22 stamina (25)" },
		Down = { "BlockPostureTaken", 1.10, "+10% posture taken when blocking" } },
	{ Id = "iron_grip", Name = "Iron Grip",
		Up = { "BlockPostureTaken", 0.85, "-15% posture taken when blocking" },
		Down = { "DodgeCost", 28, "Dodge costs 28 stamina (25)" } },
	{ Id = "second_wind", Name = "Second Wind",
		Up = { "RegenDelay", 0.45, "Stamina returns after 0.45 s (0.6)" },
		Down = { "MaxStamina", 92, "Max stamina 92 (100)" } },
	{ Id = "deep_lungs", Name = "Deep Lungs",
		Up = { "MaxStamina", 110, "Max stamina 110 (100)" },
		Down = { "StaminaRegen", 36, "Stamina refills at 36/s (40)" } },
	{ Id = "hawk_eyed", Name = "Hawk-eyed",
		Up = { "ParryWindow", 11, "Parry window 11 frames (10)" },
		Down = { "WhiffRecovery", 22, "Missed parry recovers in 22 frames (18)" } },
	{ Id = "steady_hand", Name = "Steady Hand",
		Up = { "LateParryWindow", 5, "Late-parry window 5 frames (4)" },
		Down = { "PerfectParryResolve", 16, "Perfect parry gives 16 Resolve (20)" } },
	{ Id = "thick_skinned", Name = "Thick-skinned",
		Up = { "DamageTaken", 0.92, "-8% damage taken" },
		Down = { "ResolveGain", 0.90, "-10% Resolve gained" } },
	{ Id = "quick_recovery", Name = "Quick Recovery",
		Up = { "GuardBrokenTime", 0.75, "Guard Broken lasts 0.75 s (0.9)" },
		Down = { "PostureDecay", 18, "Posture recovers at 18/s (20)" } },
	{ Id = "unshaken", Name = "Unshaken",
		Up = { "PostureDecayDelay", 1.2, "Posture starts recovering after 1.2 s (1.5)" },
		Down = { "DamageTaken", 1.05, "+5% damage taken" } },
	{ Id = "fleet", Name = "Fleet",
		Up = { "SprintCost", 10, "Sprinting costs 10 stamina/s (12)" },
		Down = { "ClimbCost", 10, "Climbing costs 10 stamina/s (8)" } },
	{ Id = "climber", Name = "Climber",
		Up = { "ClimbCost", 6, "Climbing costs 6 stamina/s (8)" },
		Down = { "SprintCost", 14, "Sprinting costs 14 stamina/s (12)" } },
	{ Id = "tinker", Name = "Tinker",
		Up = { "GearWear", 0.80, "-20% weapon and armour wear" },
		Down = { "RepairCost", 1.15, "Repairs cost 15% more" } },
	{ Id = "haggler", Name = "Haggler",
		Up = { "ShopPrices", 0.92, "Shop prices -8%" },
		Down = { "QuestGold", 0.95, "Quest gold -5%" } },
	{ Id = "hardy", Name = "Hardy",
		Up = { "AilmentBuildup", 0.80, "Ailments build up 20% slower" },
		Down = { "TonicHealing", 0.90, "Tonics heal 10% less" } },
	{ Id = "battle_born", Name = "Battle-born",
		Up = { "ResolvePerHit", 3.6, "+20% Resolve from landed hits" },
		Down = { "ResolveFade", 1.25, "Resolve fades 25% faster out of combat" } },
	{ Id = "beast_friend", Name = "Beast-friend",
		Up = { "MountBond", 1.20, "Mount bond grows 20% faster" },
		Down = { "BanditNotice", 1.10, "Bandits notice you 10% sooner" } },
}

function Traits.Find(id: any)
	for _, trait in ipairs(Traits.List) do
		if trait.Id == id then
			return trait
		end
	end
	return nil
end

-- A player's value of a stat given their trait ids (unknown ids are ignored). When two traits set the same stat
-- (e.g. Light-footed and Iron Grip both touch DodgeCost) their changes add up.
function Traits.Value(stat: string, traitIds: { string }?): number
	local info = Traits.Stats[stat]
	assert(info, "unknown stat " .. tostring(stat))
	local value = info.Base
	for _, id in ipairs(traitIds or {}) do
		local trait = Traits.Find(id)
		if trait then
			for _, change in ipairs({ trait.Up, trait.Down }) do
				if change[1] == stat then
					value += change[2] - info.Base
				end
			end
		end
	end
	return value
end

-- True when `value` is better than the stat's base.
function Traits.IsBetter(stat: string, value: number): boolean
	local info = Traits.Stats[stat]
	return if info.Better == "lower" then value < info.Base else value > info.Base
end

return Traits
