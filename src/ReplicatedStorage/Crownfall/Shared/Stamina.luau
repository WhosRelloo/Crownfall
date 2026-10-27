-- Stamina: limits how much a player can do. Pure logic; the caller passes the current time.
local Config = require(script.Parent.Config)

local Stamina = {}
Stamina.__index = Stamina

function Stamina.new(max: number?)
	local m = max or Config.Stamina.Max
	return setmetatable({ max = m, value = m, lastSpendAt = -math.huge, exhaustedUntil = -math.huge }, Stamina)
end

function Stamina:IsExhausted(now: number): boolean
	return now < self.exhaustedUntil
end

-- Allowed while any stamina is left (the last action may overdraw to 0); refused while exhausted.
function Stamina:Spend(cost: number, now: number): boolean
	if self:IsExhausted(now) or self.value <= 0 then
		return false
	end
	self.value = math.max(self.value - cost, 0)
	self.lastSpendAt = now
	if self.value == 0 then
		self.exhaustedUntil = now + Config.Stamina.ExhaustedTime
	end
	return true
end

-- Continuous costs such as sprinting and climbing.
function Stamina:Drain(perSecond: number, dt: number, now: number): boolean
	return self:Spend(perSecond * dt, now)
end

function Stamina:Update(now: number, dt: number)
	if now - self.lastSpendAt >= Config.Stamina.RegenDelay then
		self.value = math.min(self.value + Config.Stamina.RegenPerSecond * dt, self.max)
	end
end

return Stamina
