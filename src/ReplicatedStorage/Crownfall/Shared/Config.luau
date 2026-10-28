-- Crownfall tuning values. Every number is a prototype starting point from Docs/Design-Blueprint.md, section 4.
local Config = {}

Config.FPS = 60

Config.Stamina = {
	Max = 100,
	RegenDelay = 0.6, -- seconds without spending before regen starts
	RegenPerSecond = 40, -- empty to full in 2.5 s
	ExhaustedTime = 1.0,
	Costs = { Dodge = 25, Step = 15, Light = 8, Heavy = 18, BlockHit = 10, SprintPerSecond = 12, ClimbPerSecond = 8 },
}

Config.Posture = {
	DecayDelay = 1.5, -- seconds without posture damage before decay starts
	DecayPerSecond = 20, -- scaled by 0.5 + health fraction
	CoopFactor = 0.6, -- non-parry posture per extra attacker
	BrokenTime = { Player = 0.9, Enemy = 1.5, Boss = 2.0 },
}

Config.Parry = {
	WindowFrames = 10, -- Longsword; weapons pass their own window
	LateFrames = 4,
	WhiffRecoveryFrames = 18,
	MaxLatencyAllowance = 0.15, -- seconds
	LatePostureDiscount = 0.5,
}

Config.Durability = {
	WarnFraction = 0.25,
	CriticalFraction = 0.10,
	DulledDamageMultiplier = 0.6, -- -40% at 0 durability; never breaks
	Wear = { Hit = 1, Block = 2, GuardBroken = 8, PerfectParry = 0.1 },
}

Config.Movement = {
	WalkSpeed = 8, -- studs/s
	SprintSpeed = 18, -- studs/s while holding Sprint (Left Shift)
	MovingSpeed = 1, -- below this the character counts as standing
}

Config.Render = {
	Art = "humanm", -- manifest in Render/Art; falls back to the code-drawn placeholder if missing
}

Config.Camera = {
	Pitch = 40, -- degrees down from horizontal
	Distance = 70, -- studs from the focus point
	FieldOfView = 20, -- narrow, so the view reads close to orthographic
	FollowSharpness = 10,
}

return Config
