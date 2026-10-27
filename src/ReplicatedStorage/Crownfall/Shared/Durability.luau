-- Weapon and armour durability (blueprint 5.6). At 0 an item is Dulled, never broken.
local Config = require(script.Parent.Config)

local Durability = {}
Durability.__index = Durability

function Durability.new(max: number, current: number?)
	return setmetatable({ max = max, value = current or max }, Durability)
end

function Durability:Wear(kind: string)
	local amount = Config.Durability.Wear[kind]
	assert(amount, "unknown wear kind " .. tostring(kind))
	self.value = math.max(self.value - amount, 0)
end

function Durability:Fraction(): number
	return self.value / self.max
end

function Durability:State(): string
	if self.value <= 0 then
		return "Dulled"
	end
	local f = self:Fraction()
	if f <= Config.Durability.CriticalFraction then
		return "Critical"
	end
	if f <= Config.Durability.WarnFraction then
		return "Warn"
	end
	return "Ok"
end

function Durability:DamageMultiplier(): number
	return if self.value <= 0 then Config.Durability.DulledDamageMultiplier else 1
end

-- fraction of max to restore (Field Whetstone = 0.3); nil = full repair at a smith or workbench.
function Durability:Repair(fraction: number?)
	self.value = if fraction then math.min(self.value + self.max * fraction, self.max) else self.max
end

return Durability
