local RS = game:GetService("ReplicatedStorage")
local ParryJudge = require(RS.Crownfall.Shared.ParryJudge)
local T = require(script.Parent.TestKit)

local spec = {}

spec["perfect inside the 10-frame window before impact"] = function()
	T.eq(ParryJudge.Judge(9.84, 10), "Perfect") -- 0.16 s early (window is 0.1667 s)
	T.eq(ParryJudge.Judge(10, 10), "Perfect")
end

spec["too early is a miss"] = function()
	T.eq(ParryJudge.Judge(9.83, 10), "Miss") -- 0.17 s early
end

spec["late within 4 frames after impact"] = function()
	T.eq(ParryJudge.Judge(10.05, 10), "Late")
	T.eq(ParryJudge.Judge(10.07, 10), "Miss")
end

spec["weapon window overrides the default"] = function()
	T.eq(ParryJudge.Judge(9.92, 10, 6), "Perfect") -- Twin Fangs: 6 frames = 0.1 s
	T.eq(ParryJudge.Judge(9.88, 10, 6), "Miss")
end

spec["whiff locks Guard for 18 frames"] = function()
	T.truthy(ParryJudge.CanPress(nil, 0))
	T.falsy(ParryJudge.CanPress(1, 1.29))
	T.truthy(ParryJudge.CanPress(1, 1.31)) -- 18 frames = 0.3 s; stay clear of the float edge
end

spec["server accepts a report within late window plus latency"] = function()
	-- deadline = impact + 4 frames (0.0667 s) + 0.08 s latency = 10.1467
	T.truthy(ParryJudge.AcceptReport("Perfect", 10.14, 10, 0.08))
	T.falsy(ParryJudge.AcceptReport("Perfect", 10.2, 10, 0.08))
end

spec["latency allowance is capped at 150 ms"] = function()
	T.falsy(ParryJudge.AcceptReport("Late", 10.3, 10, 0.4))
	T.truthy(ParryJudge.AcceptReport("Late", 10.2, 10, 0.4))
end

spec["a miss is never accepted"] = function()
	T.falsy(ParryJudge.AcceptReport("Miss", 10, 10, 0))
end

return spec
