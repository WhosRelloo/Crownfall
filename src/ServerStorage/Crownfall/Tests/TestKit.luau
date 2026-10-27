-- Tiny assertion kit for Crownfall specs. Each check errors with a readable message on failure.
local TestKit = {}

local function show(v: any): string
	return if typeof(v) == "string" then string.format("%q", v) else tostring(v)
end

local function prefix(label: string?): string
	return if label then label .. ": " else ""
end

function TestKit.eq(actual: any, expected: any, label: string?)
	if actual ~= expected then
		error(prefix(label) .. "expected " .. show(expected) .. ", got " .. show(actual), 2)
	end
end

function TestKit.near(actual: any, expected: number, eps: number?, label: string?)
	local e = eps or 1e-6
	if typeof(actual) ~= "number" or math.abs(actual - expected) > e then
		error(prefix(label) .. "expected " .. show(expected) .. " ± " .. show(e) .. ", got " .. show(actual), 2)
	end
end

function TestKit.truthy(v: any, label: string?)
	if not v then
		error(prefix(label) .. "expected truthy, got " .. show(v), 2)
	end
end

function TestKit.falsy(v: any, label: string?)
	if v then
		error(prefix(label) .. "expected falsy, got " .. show(v), 2)
	end
end

return TestKit
