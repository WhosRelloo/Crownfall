-- Posture: how close a fighter is to losing the exchange. Full posture = Posture Break.
local Config = require(script.Parent.Config)

local Posture = {}
Posture.__index = Posture

function Posture.new(max: number, kind: string)
	assert(Config.Posture.BrokenTime[kind], "unknown posture kind " .. tostring(kind))
	return setmetatable({ max = max, value = 0, kind = kind, lastHitAt = -math.huge, brokenUntil = -math.huge }, Posture)
end

function Posture:IsBroken(now: number): boolean
	return now < self.brokenUntil
end

-- Returns true when this hit broke posture. Hits while broken are ignored.
function Posture:Add(amount: number, now: number): boolean
	if self:IsBroken(now) then
		return false
	end
	self.value = math.min(self.value + amount, self.max)
	self.lastHitAt = now
	if self.value >= self.max then
		self.brokenUntil = now + Config.Posture.BrokenTime[self.kind]
		return true
	end
	return false
end

-- healthFraction 0..1: high health recovers faster (0.5x at 0 health, 1.5x at full).
function Posture:Update(now: number, dt: number, healthFraction: number)
	if self.value >= self.max then
		if not self:IsBroken(now) then
			self.value = 0
		end
		return
	end
	if now - self.lastHitAt >= Config.Posture.DecayDelay then
		local rate = Config.Posture.DecayPerSecond * (0.5 + healthFraction)
		self.value = math.max(self.value - rate * dt, 0)
	end
end

-- Posture multiplier for a non-parry hit while `attackers` players hit the same target. Parries always use 1.
function Posture.CoopScale(attackers: number): number
	if attackers <= 1 then
		return 1
	end
	return Config.Posture.CoopFactor ^ (attackers - 1)
end

return Posture
