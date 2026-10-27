local T = require(script.Parent.TestKit)

local function fails(fn): boolean
	return not pcall(fn)
end

local spec = {}

spec["eq passes on equal values"] = function()
	T.eq(1 + 1, 2)
end

spec["eq fails on different values"] = function()
	assert(fails(function() T.eq(1, 2) end), "eq(1, 2) should fail")
end

spec["near allows a small difference"] = function()
	T.near(0.1 + 0.2, 0.3, 1e-9)
	assert(fails(function() T.near(1, 1.1, 0.01) end), "near(1, 1.1, 0.01) should fail")
end

spec["truthy and falsy"] = function()
	T.truthy(true)
	T.falsy(false)
	T.falsy(nil)
	assert(fails(function() T.truthy(nil) end), "truthy(nil) should fail")
	assert(fails(function() T.falsy(1) end), "falsy(1) should fail")
end

return spec
