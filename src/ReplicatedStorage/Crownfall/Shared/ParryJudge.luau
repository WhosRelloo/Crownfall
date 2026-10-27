-- Parry timing rules (blueprint 4.2 and 4.9). Times are seconds on one clock.
local Config = require(script.Parent.Config)

local FRAME = 1 / Config.FPS

local ParryJudge = {}

-- Perfect: a Guard tap from windowFrames before impact up to impact. Late: up to LateFrames after.
function ParryJudge.Judge(pressAt: number, impactAt: number, windowFrames: number?): string
	local window = (windowFrames or Config.Parry.WindowFrames) * FRAME
	local late = Config.Parry.LateFrames * FRAME
	local d = pressAt - impactAt
	if d >= -window and d <= 0 then
		return "Perfect"
	end
	if d > 0 and d <= late then
		return "Late"
	end
	return "Miss"
end

-- After a mistimed tap, Guard is locked for WhiffRecoveryFrames so mashing never works.
function ParryJudge.CanPress(lastMissAt: number?, now: number): boolean
	return lastMissAt == nil or now - lastMissAt >= Config.Parry.WhiffRecoveryFrames * FRAME
end

-- Server check on a client's own parry judgement (defender-favoured). Accepted if the report arrived
-- by impact + late window + the player's latency, with the latency allowance capped.
function ParryJudge.AcceptReport(result: string, receivedAt: number, impactAt: number, latency: number): boolean
	if result ~= "Perfect" and result ~= "Late" then
		return false
	end
	local allowance = math.clamp(latency, 0, Config.Parry.MaxLatencyAllowance)
	return receivedAt <= impactAt + Config.Parry.LateFrames * FRAME + allowance
end

return ParryJudge
