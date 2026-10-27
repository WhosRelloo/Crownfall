# Prototype Milestone 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Place1, a player walks around as a 2.5D placeholder pixel sprite under a fixed three-quarter camera, and the core combat rules (stamina, posture, parry timing, durability) exist as tested modules.

**Architecture:** The repo is the source of truth. `Tools/studio.py` pushes `src/` into the Studio window named exactly "Place1". It deletes and rebuilds every folder named `Crownfall`, so scripts are always new instances and nothing is edited in place. Game rules are pure Luau modules that take time as an argument, so tests can run in Edit mode. Rendering is client-side: each character's Roblox body is hidden and a camera-facing "sprite card" Part with a SurfaceGui draws the pixel art.

**Tech Stack:** Roblox Studio + Luau, Python 3 (Tools/studio.py talks to Studio's own StudioMCP.exe over stdio), Git.

**Spec:** `Docs/Design-Blueprint.md`, mainly section 4 (combat and movement), 13.1 (prototype) and the Platform assumption (2.5D).

## Global Constraints

- Only ever touch the Crownfall place (**placeId 93979562442002**, formerly named Place1). `Tools/studio.py` matches it by place id and refuses any other.
- The whole game is **2.5D**: pixel sprites in a 3D collision world, with a fixed three-quarter camera.
- Never edit a script's source in place in Studio. Change the file in `src/`, then run `python -I Tools/studio.py sync`.
- Only sync while Studio is in Edit mode, never during Play.
- Every file under `src/` must sit inside a folder named `Crownfall`. Sync deletes and rebuilds those folders, so nothing made by hand may live inside them.
- File suffixes: `X.server.luau` → Script, `X.client.luau` → LocalScript, `X.luau` → ModuleScript.
- All tuning numbers live in `Shared/Config.luau`, with values copied from the blueprint: parry 10 frames, late 4 frames, whiff lockout 18 frames, latency cap 150 ms, stamina 100 with dodge 25, regen delay 0.6 s and full in about 2.5 s, posture decay delay 1.5 s, broken times Player 0.9 s / Enemy 1.5 s / Boss 2.0 s, durability warn 25% / critical 10% / Dulled −40%.
- Placeholder art only for now. Real sprite sheets replace `Render/HeroSprite.luau` later without changes to the renderer.
- Run every command from the repo root `C:/Users/Owner/Documents/Crownfall`.

## Prototype milestone map

The prototype (blueprint 13.1) is built in six milestones. Each milestone gets its own detailed plan when it starts. This document is the plan for M1 only.

| Milestone | Delivers |
| --- | --- |
| **M1 Foundation (this plan)** | Sync and test tooling, core rule modules, 2.5D camera, placeholder sprite character |
| M2 Movement | Sprint, dodge with i-frames, jump, roll-landing, stamina HUD |
| M3 Combat core | Attacks, block, parry, posture bars, Critical, telegraph categories, hit-stop, durability HUD, server-validated parry reports |
| M4 Enemies | Encounter Director with attack tokens; Swordsman, Shieldbearer and Archer; Bandit Chief miniboss with a Grab unblockable |
| M5 Traversal and level | Directional climbing with corners and a rest ledge, one rooftop Runner Route, the Shrine Yard blockout |
| M6 Multiplayer and feel gate | 2–4 player encounter, simulated latency, parry mismatch logging, the 13.1 success-criteria playtest |

## File map (M1)

| File | Responsibility |
| --- | --- |
| `Tools/studio.py` | Find "Place1", sync `src/`, run tests, run a Luau file |
| `src/ServerStorage/Crownfall/Tests/TestKit.luau` | Assertions for specs |
| `src/ServerStorage/Crownfall/Tests/*.spec.luau` | One spec module per rule module |
| `src/ReplicatedStorage/Crownfall/Shared/Config.luau` | Every tuning number |
| `src/ReplicatedStorage/Crownfall/Shared/Stamina.luau` | Stamina spend, drain, exhaustion, regen |
| `src/ReplicatedStorage/Crownfall/Shared/Posture.luau` | Posture build-up, break, decay, co-op scaling |
| `src/ReplicatedStorage/Crownfall/Shared/ParryJudge.luau` | Perfect / Late / Miss, whiff lockout, server acceptance |
| `src/ReplicatedStorage/Crownfall/Shared/Durability.luau` | Wear, states, Dulled multiplier, repair |
| `src/ReplicatedStorage/Crownfall/Render/CameraMath.luau` | Camera offset, world → screen direction |
| `src/ReplicatedStorage/Crownfall/Render/Facing.luau` | Screen direction → sprite sheet + mirror |
| `src/ReplicatedStorage/Crownfall/Render/PixelArt.luau` | Rows of palette letters → horizontal pixel runs |
| `src/ReplicatedStorage/Crownfall/Render/HeroSprite.luau` | Placeholder hero art data |
| `src/ReplicatedStorage/Crownfall/Render/SpriteCard.luau` | Camera-facing card Part that draws a frame |
| `src/StarterPlayer/StarterPlayerScripts/Crownfall/CameraController.client.luau` | Fixed three-quarter camera |
| `src/StarterPlayer/StarterPlayerScripts/Crownfall/CharacterSprites.client.luau` | Hides bodies, drives a sprite card per character |

---

### Task 1: Studio tooling and test runner

**Files:**
- Create: `Tools/studio.py`
- Create: `src/ServerStorage/Crownfall/Tests/TestKit.luau`
- Test: `src/ServerStorage/Crownfall/Tests/TestKit.spec.luau`

**Interfaces:**
- Produces: `python -I Tools/studio.py sync`, `python -I Tools/studio.py test [filter]` (exit code 1 on any failure), `python -I Tools/studio.py luau <Edit|Server|Client> @file.luau`.
- Produces: `TestKit.eq(actual, expected, label?)`, `TestKit.near(actual, expected, eps?, label?)`, `TestKit.truthy(v, label?)`, `TestKit.falsy(v, label?)`. Each one errors on failure.
- Produces the spec contract: a `*.spec` ModuleScript in `ServerStorage.Crownfall.Tests` returns `{ [testName: string]: () -> () }`.

- [ ] **Step 1: Write `Tools/studio.py`**

```python
"""Crownfall Studio bridge. Only ever talks to the Crownfall place (placeId 93979562442002, formerly "Place1").

python -I Tools/studio.py sync                     rebuild every "Crownfall" folder in Place1 from src/
python -I Tools/studio.py test [filter]            run *.spec modules in ServerStorage.Crownfall.Tests
python -I Tools/studio.py luau <Edit|Server|Client> @file.luau   run a Luau file in Place1

Runs its own StudioMCP.exe (the newest under %LOCALAPPDATA%\\Roblox\\Versions) next to any other MCP client.
"""
import glob, json, os, queue, re, subprocess, sys, threading, time

PLACE = "placeId: 93979562442002"  # the Crownfall place (formerly "Place1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
EXE = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions\*\StudioMCP.exe")), key=os.path.getmtime)[-1]


class Client:
    def __init__(self):
        self.p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        self.n = 0
        self.req("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "crownfall-tools", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read(self):
        for line in self.p.stdout:
            line = line.strip()
            if line:
                try:
                    self.q.put(json.loads(line))
                except ValueError:
                    pass

    def send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def req(self, method, params, timeout=300):
        self.n += 1
        my = self.n
        self.send({"jsonrpc": "2.0", "id": my, "method": method, "params": params})
        while True:
            msg = self.q.get(timeout=timeout)
            if msg.get("id") == my:
                return msg

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


def studio_id(c):
    items = []
    for _ in range(10):  # Studio names can read null for a moment
        r = c.req("tools/call", {"name": "list_roblox_studios", "arguments": {}})
        data = json.loads(r["result"]["content"][0]["text"])
        items = data if isinstance(data, list) else data.get("studios") or []
        hits = [i for i in items if PLACE in (i.get("name") or "")]
        if len(hits) == 1:
            return hits[0]["id"]
        time.sleep(2)
    sys.exit(f'Studio window "{PLACE}" not found exactly once: {[i.get("name") for i in items]}')


def run_luau(c, code, datamodel="Edit"):
    args = {"code": code, "datamodel_type": datamodel, "studio_id": studio_id(c)}
    r = c.req("tools/call", {"name": "execute_luau", "arguments": args}, timeout=600)
    res = r.get("result") or r.get("error") or {}
    text = "\n".join(p["text"] for p in res.get("content") or [] if p.get("type") == "text")
    return text, bool(res.get("isError"))


def long_string(s):
    level = 0
    while ("]" + "=" * level + "]") in (s + "]"):
        level += 1
    eq = "=" * level
    return f"[{eq}[\n{s}]{eq}]"  # Luau drops the newline right after the opening bracket


def collect():
    entries = []
    for dirpath, _, files in os.walk(SRC):
        for f in sorted(files):
            if not f.endswith(".luau"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), SRC).replace("\\", "/")
            parts = rel.split("/")
            name, cls = parts[-1][:-len(".luau")], "ModuleScript"
            if name.endswith(".server"):
                name, cls = name[:-len(".server")], "Script"
            elif name.endswith(".client"):
                name, cls = name[:-len(".client")], "LocalScript"
            if "Crownfall" not in parts[1:-1]:
                sys.exit(f"{rel}: every file must live inside a folder named Crownfall")
            with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                entries.append((parts[:-1] + [name], cls, fh.read()))
    return entries


SYNC = r"""
local entries = {__ENTRIES__}
local roots = {}
for _, e in ipairs(entries) do
	local node = game:GetService(e.path[1])
	for i = 2, #e.path - 1 do
		if e.path[i] == "Crownfall" then
			local key = table.concat(e.path, "/", 1, i)
			if not roots[key] then
				roots[key] = true
				local old = node:FindFirstChild("Crownfall")
				if old then old:Destroy() end
			end
			break
		end
		node = node:FindFirstChild(e.path[i]) or error("missing " .. table.concat(e.path, ".", 1, i))
	end
end
local rootCount = 0
for _ in pairs(roots) do rootCount += 1 end
for _, e in ipairs(entries) do
	local node = game:GetService(e.path[1])
	for i = 2, #e.path - 1 do
		local nextNode = node:FindFirstChild(e.path[i])
		if not nextNode then
			nextNode = Instance.new("Folder")
			nextNode.Name = e.path[i]
			nextNode.Parent = node
		end
		node = nextNode
	end
	local s = Instance.new(e.class)
	s.Name = e.path[#e.path]
	s.Source = e.source
	s.Parent = node
end
return ("synced %d scripts into %d Crownfall folders"):format(#entries, rootCount)
"""

TEST = r"""
local FILTER = __FILTER__
local crown = game:GetService("ServerStorage"):FindFirstChild("Crownfall")
local tests = crown and crown:FindFirstChild("Tests")
assert(tests, "ServerStorage.Crownfall.Tests is missing: run sync first")
local lines, passed, failed = {}, 0, 0
local modules = tests:GetChildren()
table.sort(modules, function(a, b) return a.Name < b.Name end)
for _, m in ipairs(modules) do
	if m:IsA("ModuleScript") and m.Name:sub(-5) == ".spec" and (FILTER == "" or string.find(m.Name, FILTER, 1, true)) then
		local ok, spec = pcall(require, m)
		if not ok then
			failed += 1
			table.insert(lines, "FAIL " .. m.Name .. " (load): " .. tostring(spec))
		else
			local names = {}
			for name in pairs(spec) do table.insert(names, name) end
			table.sort(names)
			for _, name in ipairs(names) do
				local ok2, err = pcall(spec[name])
				if ok2 then
					passed += 1
					table.insert(lines, "PASS " .. m.Name .. " > " .. name)
				else
					failed += 1
					table.insert(lines, "FAIL " .. m.Name .. " > " .. name .. ": " .. tostring(err))
				end
			end
		end
	end
end
table.insert(lines, ("%d passed, %d failed"):format(passed, failed))
return table.concat(lines, "\n")
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("sync", "test", "luau"):
        sys.exit(__doc__)
    c = Client()
    try:
        cmd = sys.argv[1]
        if cmd == "sync":
            parts = []
            for path, cls, src in collect():
                parts.append("{path={%s}, class=%s, source=%s}" % (
                    ", ".join(json.dumps(p) for p in path), json.dumps(cls), long_string(src)))
            text, err = run_luau(c, SYNC.replace("__ENTRIES__", ",\n".join(parts)))
        elif cmd == "test":
            flt = sys.argv[2] if len(sys.argv) > 2 else ""
            text, err = run_luau(c, TEST.replace("__FILTER__", json.dumps(flt)))
            m = re.search(r"(\d+) passed, (\d+) failed", text)
            err = err or not m or int(m.group(2)) > 0 or int(m.group(1)) == 0
        else:
            with open(sys.argv[3][1:], encoding="utf-8") as fh:
                text, err = run_luau(c, fh.read(), sys.argv[2])
        print(text)
        sys.exit(1 if err else 0)
    finally:
        c.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing spec `src/ServerStorage/Crownfall/Tests/TestKit.spec.luau`**

```lua
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
```

- [ ] **Step 3: Check Studio is in Edit mode, then sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync`
Expected: `synced 1 scripts into 1 Crownfall folders`

Run: `python -I Tools/studio.py test`
Expected: exit code 1 with `FAIL TestKit.spec (load): ... TestKit is not a valid member of Folder` and `0 passed, 1 failed`.

- [ ] **Step 4: Write `src/ServerStorage/Crownfall/Tests/TestKit.luau`**

```lua
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
```

- [ ] **Step 5: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test`
Expected: four `PASS TestKit.spec > ...` lines and `4 passed, 0 failed`, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add Tools/studio.py src/ServerStorage/Crownfall/Tests/TestKit.luau src/ServerStorage/Crownfall/Tests/TestKit.spec.luau
git commit -m "Add Studio sync/test tooling and TestKit"
```

### Task 2: Config and Stamina

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Shared/Config.luau`
- Create: `src/ReplicatedStorage/Crownfall/Shared/Stamina.luau`
- Test: `src/ServerStorage/Crownfall/Tests/Stamina.spec.luau`

**Interfaces:**
- Consumes: TestKit (Task 1).
- Produces: `Config` table (shape below; later tasks read `Config.Posture`, `Config.Parry`, `Config.Durability`, `Config.Camera`, `Config.FPS`).
- Produces: `Stamina.new(max: number?) -> Stamina` with fields `max`, `value`; methods `:Spend(cost, now) -> boolean`, `:Drain(perSecond, dt, now) -> boolean`, `:Update(now, dt)`, `:IsExhausted(now) -> boolean`. `now` is seconds on any clock the caller chooses.

- [ ] **Step 1: Write the failing spec `src/ServerStorage/Crownfall/Tests/Stamina.spec.luau`**

```lua
local RS = game:GetService("ReplicatedStorage")
local Stamina = require(RS.Crownfall.Shared.Stamina)
local T = require(script.Parent.TestKit)

local spec = {}

spec["starts full"] = function()
	T.eq(Stamina.new(100).value, 100)
end

spec["spend subtracts the cost"] = function()
	local s = Stamina.new(100)
	T.truthy(s:Spend(25, 0))
	T.eq(s.value, 75)
end

spec["overdraw empties and exhausts for 1 s"] = function()
	local s = Stamina.new(100)
	s.value = 10
	T.truthy(s:Spend(25, 5), "the last action may overdraw")
	T.eq(s.value, 0)
	T.truthy(s:IsExhausted(5.5))
	T.falsy(s:IsExhausted(6.0))
	T.falsy(s:Spend(8, 5.5), "refused while exhausted")
end

spec["no regen before the 0.6 s delay"] = function()
	local s = Stamina.new(100)
	s:Spend(50, 0)
	s:Update(0.5, 0.5)
	T.eq(s.value, 50)
end

spec["regen after the delay, capped at max"] = function()
	local s = Stamina.new(100)
	s:Spend(50, 0)
	s:Update(0.6, 1.0)
	T.eq(s.value, 90)
	s:Update(2, 1)
	T.eq(s.value, 100)
end

spec["empty to full in about 2.5 s after the delay"] = function()
	local s = Stamina.new(100)
	s.value = 1
	s:Spend(25, 0)
	local t = 0.6
	for _ = 1, 25 do
		s:Update(t, 0.1)
		t += 0.1
	end
	T.near(s.value, 100, 1e-6)
end

spec["drain spends per second"] = function()
	local s = Stamina.new(100)
	T.truthy(s:Drain(12, 0.5, 0))
	T.eq(s.value, 94)
end

return spec
```

- [ ] **Step 2: Sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Stamina`
Expected: exit 1, `FAIL Stamina.spec (load): ... Crownfall is not a valid member of ReplicatedStorage`.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Shared/Config.luau`**

```lua
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

Config.Camera = {
	Pitch = 40, -- degrees down from horizontal
	Distance = 70, -- studs from the focus point
	FieldOfView = 20, -- narrow, so the view reads close to orthographic
	FollowSharpness = 10,
}

return Config
```

- [ ] **Step 4: Write `src/ReplicatedStorage/Crownfall/Shared/Stamina.luau`**

```lua
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
```

- [ ] **Step 5: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Stamina`
Expected: `7 passed, 0 failed`.

- [ ] **Step 6: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Shared/Config.luau src/ReplicatedStorage/Crownfall/Shared/Stamina.luau src/ServerStorage/Crownfall/Tests/Stamina.spec.luau
git commit -m "Add Config and Stamina rules"
```

### Task 3: Posture

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Shared/Posture.luau`
- Test: `src/ServerStorage/Crownfall/Tests/Posture.spec.luau`

**Interfaces:**
- Consumes: `Config.Posture` (Task 2).
- Produces: `Posture.new(max: number, kind: "Player" | "Enemy" | "Boss") -> Posture` with fields `max`, `value`; methods `:Add(amount, now) -> boolean` (true when this hit broke posture), `:IsBroken(now) -> boolean`, `:Update(now, dt, healthFraction)`; static `Posture.CoopScale(attackers: number) -> number`.

- [ ] **Step 1: Write the failing spec `src/ServerStorage/Crownfall/Tests/Posture.spec.luau`**

```lua
local RS = game:GetService("ReplicatedStorage")
local Posture = require(RS.Crownfall.Shared.Posture)
local T = require(script.Parent.TestKit)

local spec = {}

spec["reaching max breaks posture once"] = function()
	local p = Posture.new(100, "Enemy")
	T.falsy(p:Add(60, 0))
	T.truthy(p:Add(60, 0.1), "this hit breaks")
	T.truthy(p:IsBroken(0.2))
	T.falsy(p:Add(10, 0.3), "hits while broken do nothing")
end

spec["enemy break lasts 1.5 s, then posture resets to 0"] = function()
	local p = Posture.new(100, "Enemy")
	p:Add(100, 0)
	p:Update(1.4, 0.1, 1)
	T.truthy(p:IsBroken(1.4))
	T.eq(p.value, 100)
	p:Update(1.5, 0.1, 1)
	T.falsy(p:IsBroken(1.5))
	T.eq(p.value, 0)
end

spec["player break lasts 0.9 s"] = function()
	local p = Posture.new(100, "Player")
	p:Add(100, 0)
	T.truthy(p:IsBroken(0.89))
	T.falsy(p:IsBroken(0.9))
end

spec["no decay within 1.5 s of the last hit"] = function()
	local p = Posture.new(100, "Enemy")
	p:Add(50, 0)
	p:Update(1.4, 1, 1)
	T.eq(p.value, 50)
end

spec["decay is 30/s at full health and 10/s at zero health"] = function()
	local full = Posture.new(100, "Enemy")
	full:Add(50, 0)
	full:Update(1.5, 1, 1)
	T.near(full.value, 20)
	local low = Posture.new(100, "Enemy")
	low:Add(50, 0)
	low:Update(1.5, 1, 0)
	T.near(low.value, 40)
end

spec["co-op scale shrinks with each extra attacker"] = function()
	T.eq(Posture.CoopScale(1), 1)
	T.near(Posture.CoopScale(2), 0.6)
	T.near(Posture.CoopScale(3), 0.36)
end

spec["unknown kind is rejected"] = function()
	T.falsy(pcall(Posture.new, 100, "Dragon"))
end

return spec
```

- [ ] **Step 2: Sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Posture`
Expected: exit 1, `FAIL Posture.spec (load): ... Posture is not a valid member of Folder`.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Shared/Posture.luau`**

```lua
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
```

- [ ] **Step 4: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Posture`
Expected: `7 passed, 0 failed`.

- [ ] **Step 5: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Shared/Posture.luau src/ServerStorage/Crownfall/Tests/Posture.spec.luau
git commit -m "Add Posture rules"
```

### Task 4: ParryJudge

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Shared/ParryJudge.luau`
- Test: `src/ServerStorage/Crownfall/Tests/ParryJudge.spec.luau`

**Interfaces:**
- Consumes: `Config.FPS`, `Config.Parry` (Task 2).
- Produces: `ParryJudge.Judge(pressAt, impactAt, windowFrames?) -> "Perfect" | "Late" | "Miss"`, `ParryJudge.CanPress(lastMissAt: number?, now) -> boolean`, `ParryJudge.AcceptReport(result, receivedAt, impactAt, latency) -> boolean`. M3 uses these on the client (Judge, CanPress) and server (AcceptReport).

- [ ] **Step 1: Write the failing spec `src/ServerStorage/Crownfall/Tests/ParryJudge.spec.luau`**

```lua
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
```

- [ ] **Step 2: Sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test ParryJudge`
Expected: exit 1, `FAIL ParryJudge.spec (load): ... ParryJudge is not a valid member of Folder`.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Shared/ParryJudge.luau`**

```lua
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
```

- [ ] **Step 4: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test ParryJudge`
Expected: `8 passed, 0 failed`.

- [ ] **Step 5: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Shared/ParryJudge.luau src/ServerStorage/Crownfall/Tests/ParryJudge.spec.luau
git commit -m "Add ParryJudge timing rules"
```

### Task 5: Durability

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Shared/Durability.luau`
- Test: `src/ServerStorage/Crownfall/Tests/Durability.spec.luau`

**Interfaces:**
- Consumes: `Config.Durability` (Task 2).
- Produces: `Durability.new(max, current?) -> Durability` with fields `max`, `value`; methods `:Wear(kind: "Hit" | "Block" | "GuardBroken" | "PerfectParry")`, `:Fraction() -> number`, `:State() -> "Ok" | "Warn" | "Critical" | "Dulled"`, `:DamageMultiplier() -> number`, `:Repair(fraction?)`.

- [ ] **Step 1: Write the failing spec `src/ServerStorage/Crownfall/Tests/Durability.spec.luau`**

```lua
local RS = game:GetService("ReplicatedStorage")
local Durability = require(RS.Crownfall.Shared.Durability)
local T = require(script.Parent.TestKit)

local spec = {}

spec["wear amounts follow the kind"] = function()
	local d = Durability.new(100)
	d:Wear("Hit")
	d:Wear("Block")
	d:Wear("GuardBroken")
	T.eq(d.value, 89)
	d:Wear("PerfectParry")
	T.near(d.value, 88.9)
end

spec["states by fraction"] = function()
	T.eq(Durability.new(100, 26):State(), "Ok")
	T.eq(Durability.new(100, 25):State(), "Warn")
	T.eq(Durability.new(100, 10):State(), "Critical")
	T.eq(Durability.new(100, 0):State(), "Dulled")
end

spec["never goes below zero and never breaks"] = function()
	local d = Durability.new(100, 3)
	d:Wear("GuardBroken")
	T.eq(d.value, 0)
	T.eq(d:State(), "Dulled")
end

spec["dulled weapons deal 60% damage"] = function()
	T.eq(Durability.new(100, 1):DamageMultiplier(), 1)
	T.near(Durability.new(100, 0):DamageMultiplier(), 0.6)
end

spec["whetstone restores 30%, smith restores fully"] = function()
	local d = Durability.new(100, 10)
	d:Repair(0.3)
	T.eq(d.value, 40)
	d:Repair(0.9)
	T.eq(d.value, 100, "capped at max")
	d.value = 5
	d:Repair()
	T.eq(d.value, 100)
end

spec["unknown wear kind is rejected"] = function()
	local d = Durability.new(100)
	T.falsy(pcall(d.Wear, d, "Lava"))
end

return spec
```

- [ ] **Step 2: Sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Durability`
Expected: exit 1, `FAIL Durability.spec (load): ... Durability is not a valid member of Folder`.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Shared/Durability.luau`**

```lua
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
```

- [ ] **Step 4: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Durability`
Expected: `6 passed, 0 failed`.

- [ ] **Step 5: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Shared/Durability.luau src/ServerStorage/Crownfall/Tests/Durability.spec.luau
git commit -m "Add Durability rules"
```

### Task 6: 2.5D render math and placeholder art data

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Render/CameraMath.luau`
- Create: `src/ReplicatedStorage/Crownfall/Render/Facing.luau`
- Create: `src/ReplicatedStorage/Crownfall/Render/PixelArt.luau`
- Create: `src/ReplicatedStorage/Crownfall/Render/HeroSprite.luau`
- Test: `src/ServerStorage/Crownfall/Tests/Render.spec.luau`

**Interfaces:**
- Produces: `CameraMath.Offset(pitchDeg, distance) -> Vector3`, `CameraMath.ToScreen(v: Vector3) -> Vector2` (x = screen right, y = screen up/away; camera yaw is fixed at 0 in M1).
- Produces: `Facing.FromScreen(dir: Vector2) -> (sheet: "S" | "N" | "E", mirror: boolean)`.
- Produces: `PixelArt.ToRuns(rows: {string}, mirror: boolean?) -> {{x: number, y: number, w: number, key: string}}` (0-based x, y; "." is empty).
- Produces the art contract (any sprite module, placeholder or real): `Width: number`, `Height: number`, `Palette: {[string]: Color3}`, `Frame(sheet: string, pose: "Idle" | "RunA" | "RunB") -> {string}`.

- [ ] **Step 1: Write the failing spec `src/ServerStorage/Crownfall/Tests/Render.spec.luau`**

```lua
local RS = game:GetService("ReplicatedStorage")
local Render = RS.Crownfall.Render -- dot access errors at once if the folder is missing (WaitForChild would hang)
local CameraMath = require(Render.CameraMath)
local Facing = require(Render.Facing)
local PixelArt = require(Render.PixelArt)
local HeroSprite = require(Render.HeroSprite)
local T = require(script.Parent.TestKit)

local spec = {}

spec["camera sits behind +Z and above the focus"] = function()
	local o = CameraMath.Offset(40, 70)
	T.near(o.X, 0)
	T.near(o.Y, math.sin(math.rad(40)) * 70)
	T.near(o.Z, math.cos(math.rad(40)) * 70)
end

spec["world motion maps to screen directions"] = function()
	local right = CameraMath.ToScreen(Vector3.new(1, 0, 0))
	T.near(right.X, 1)
	T.near(right.Y, 0)
	local away = CameraMath.ToScreen(Vector3.new(0, 0, -1))
	T.near(away.X, 0)
	T.near(away.Y, 1)
end

spec["facing picks sheet and mirror"] = function()
	local function check(x, y, sheet, mirror)
		local s, m = Facing.FromScreen(Vector2.new(x, y))
		T.eq(s, sheet, ("(%d, %d) sheet"):format(x, y))
		T.eq(m, mirror, ("(%d, %d) mirror"):format(x, y))
	end
	check(0, 1, "N", false)
	check(0, -1, "S", false)
	check(1, 0, "E", false)
	check(-1, 0, "E", true)
	check(1, 1, "E", false)
	check(-1, -1, "E", true)
end

spec["runs merge same-colour pixels and skip empty ones"] = function()
	local runs = PixelArt.ToRuns({ "aab.", ".bbb" })
	T.eq(#runs, 3)
	T.eq(runs[1].x, 0); T.eq(runs[1].w, 2); T.eq(runs[1].key, "a")
	T.eq(runs[2].x, 2); T.eq(runs[2].w, 1); T.eq(runs[2].key, "b")
	T.eq(runs[3].x, 1); T.eq(runs[3].y, 1); T.eq(runs[3].w, 3)
end

spec["mirror flips runs left to right"] = function()
	local runs = PixelArt.ToRuns({ "aa.." }, true)
	T.eq(runs[1].x, 2)
	T.eq(runs[1].w, 2)
end

spec["uneven rows are rejected"] = function()
	T.falsy(pcall(PixelArt.ToRuns, { "aaa", "aa" }))
end

spec["every hero frame is 12x20 and uses only palette colours"] = function()
	for _, sheet in ipairs({ "S", "N", "E" }) do
		for _, pose in ipairs({ "Idle", "RunA", "RunB" }) do
			local rows = HeroSprite.Frame(sheet, pose)
			T.eq(#rows, HeroSprite.Height, sheet .. "/" .. pose .. " rows")
			for i, row in ipairs(rows) do
				T.eq(#row, HeroSprite.Width, ("%s/%s row %d width"):format(sheet, pose, i))
				for c in row:gmatch("[^%.]") do
					T.truthy(HeroSprite.Palette[c], ("%s/%s colour %q"):format(sheet, pose, c))
				end
			end
		end
	end
end

return spec
```

- [ ] **Step 2: Sync and run the test to verify it fails**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Render`
Expected: exit 1, `FAIL Render.spec (load): ... Render is not a valid member of Folder`.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Render/CameraMath.luau`**

```lua
-- Geometry for the fixed three-quarter camera. Camera yaw is fixed at 0 in M1: the camera sits on +Z
-- looking toward -Z, so screen-right is +X and screen-up (away from the viewer) is -Z.
local CameraMath = {}

function CameraMath.Offset(pitchDeg: number, distance: number): Vector3
	local p = math.rad(pitchDeg)
	return Vector3.new(0, math.sin(p) * distance, math.cos(p) * distance)
end

function CameraMath.ToScreen(v: Vector3): Vector2
	return Vector2.new(v.X, -v.Z)
end

return CameraMath
```

- [ ] **Step 4: Write `src/ReplicatedStorage/Crownfall/Render/Facing.luau`**

```lua
-- Screen direction -> which drawn sheet to show and whether to mirror it.
-- Placeholder art has 3 sheets: "S" (toward the camera), "N" (away), "E" (side). West is East mirrored.
local Facing = {}

function Facing.FromScreen(dir: Vector2): (string, boolean)
	local angle = math.deg(math.atan2(dir.X, dir.Y)) -- 0 = away (N), 90 = right (E)
	if math.abs(angle) <= 30 then
		return "N", false
	end
	if math.abs(angle) >= 150 then
		return "S", false
	end
	if angle > 0 then
		return "E", false
	end
	return "E", true
end

return Facing
```

- [ ] **Step 5: Write `src/ReplicatedStorage/Crownfall/Render/PixelArt.luau`**

```lua
-- Turns rows of palette letters into horizontal runs, so a sprite draws as few Frames as possible.
-- "." is an empty pixel. Returned x and y are 0-based; mirror flips left and right.
local PixelArt = {}

function PixelArt.ToRuns(rows: { string }, mirror: boolean?): { { x: number, y: number, w: number, key: string } }
	local runs = {}
	local width = #rows[1]
	for y, row in ipairs(rows) do
		assert(#row == width, ("row %d is %d wide, expected %d"):format(y, #row, width))
		local x = 1
		while x <= width do
			local key = row:sub(x, x)
			local stop = x
			while stop < width and row:sub(stop + 1, stop + 1) == key do
				stop += 1
			end
			if key ~= "." then
				local left = if mirror then width - stop else x - 1
				table.insert(runs, { x = left, y = y - 1, w = stop - x + 1, key = key })
			end
			x = stop + 1
		end
	end
	return runs
end

return PixelArt
```

- [ ] **Step 6: Write `src/ReplicatedStorage/Crownfall/Render/HeroSprite.luau`**

```lua
-- Placeholder hero: 12 x 20 sprite pixels, 3 drawn sheets (S, N, E; West = East mirrored).
-- Real pixel art replaces this module later. The renderer only needs Width, Height, Palette and Frame().
local HeroSprite = {}

HeroSprite.Width = 12
HeroSprite.Height = 20
HeroSprite.Palette = {
	h = Color3.fromRGB(60, 40, 30), -- hair
	s = Color3.fromRGB(235, 190, 150), -- skin
	e = Color3.fromRGB(30, 30, 40), -- eyes
	c = Color3.fromRGB(40, 70, 140), -- cloak (Varrow lapis)
	a = Color3.fromRGB(170, 175, 185), -- armour
	l = Color3.fromRGB(70, 60, 55), -- legs
	b = Color3.fromRGB(45, 35, 30), -- boots
	w = Color3.fromRGB(210, 215, 225), -- sword
}

local BLANK = "............"

-- Rows 1-14: head and torso.
local BODY = {
	S = {
		"....hhhh....",
		"...hhhhhh...",
		"...hssssh...",
		"...sesses...",
		"...ssssss...",
		"....ssss....",
		"..cccccccc..",
		".cccaaaaccc.",
		".ccaaaaaacc.",
		".scaaaaaacs.",
		".scaaaaaacs.",
		".s.aaaaaa.s.",
		"...cccccc...",
		"...cccccc...",
	},
	N = {
		"....hhhh....",
		"...hhhhhh...",
		"...hhhhhh...",
		"...hhhhhh...",
		"...hhhhhh...",
		"....ssss....",
		"..cccccccc..",
		".cccccccccc.",
		".cccccccccc.",
		".sccccccccs.",
		".sccccccccs.",
		"..cccccccc..",
		"...cccccc...",
		"...cccccc...",
	},
	E = {
		".....hhhh...",
		"....hhhhhh..",
		"....hhssss..",
		"....hhsses..",
		"....hsssss..",
		".....sss....",
		"....cccccc..",
		"...cccaaaa..",
		"...ccaaaaas.",
		"...ccaaaaasw",
		"...ccaaaaa.w",
		"...cccaaaa.w",
		"....cccccc.w",
		"....cccccc..",
	},
}

-- Rows 15-19: legs per pose.
local FRONT_LEGS = {
	Idle = { "...ll..ll...", "...ll..ll...", "...ll..ll...", "...bb..bb...", "..bbb..bbb.." },
	RunA = { "...ll...ll..", "..ll....ll..", "..ll.....ll.", "..bb.....bb.", ".bbb.....bbb" },
	RunB = { "....llll....", "....llll....", "....ll.ll...", "....bb.bb...", "...bbb.bbb.." },
}

local LEGS = {
	S = FRONT_LEGS,
	N = FRONT_LEGS,
	E = {
		Idle = { "....ll.ll...", "....ll.ll...", "....ll.ll...", "....bb.bbb..", "...bbb.bbb.." },
		RunA = { "....ll..ll..", "...ll....ll.", "..ll.....ll.", "..bb.....bbb", ".bbb........" },
		RunB = { "....llll....", "....llll....", ".....ll.....", ".....bbb....", "....bbbb...." },
	},
}

function HeroSprite.Frame(sheet: string, pose: string): { string }
	local rows = table.clone(BODY[sheet])
	for _, row in ipairs(LEGS[sheet][pose]) do
		table.insert(rows, row)
	end
	table.insert(rows, BLANK)
	return rows
end

return HeroSprite
```

- [ ] **Step 7: Sync and run the test to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test Render`
Expected: `7 passed, 0 failed`.

- [ ] **Step 8: Run the whole suite**

Run: `python -I Tools/studio.py test`
Expected: `39 passed, 0 failed` (TestKit 4, Stamina 7, Posture 7, ParryJudge 8, Durability 6, Render 7).

- [ ] **Step 9: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Render src/ServerStorage/Crownfall/Tests/Render.spec.luau
git commit -m "Add 2.5D render math and placeholder hero art"
```

### Task 7: Sprite card, camera and character sprites in Play

**Files:**
- Create: `src/ReplicatedStorage/Crownfall/Render/SpriteCard.luau`
- Create: `src/StarterPlayer/StarterPlayerScripts/Crownfall/CameraController.client.luau`
- Create: `src/StarterPlayer/StarterPlayerScripts/Crownfall/CharacterSprites.client.luau`
- Test: `Tools/checks/m1_play.luau` (a Client-datamodel check run during Play)

**Interfaces:**
- Consumes: `Config.Camera` (Task 2); `CameraMath`, `Facing`, `PixelArt`, `HeroSprite` (Task 6).
- Produces: `SpriteCard.new(art, parent: Instance) -> SpriteCard`, `:Show(sheet, pose, mirror)`, `:Place(foot: Vector3, cameraCFrame: CFrame)`, `:Destroy()`. Field `part` is the card BasePart.
- Produces in Play: a client-only `Workspace.CrownfallSprites` folder with one `SpriteCard` Part per character; camera is `Scriptable`.

- [ ] **Step 1: Write the failing Play check `Tools/checks/m1_play.luau`**

```lua
-- Run in the Client datamodel while Place1 is in Play. Returns PASS/FAIL lines.
local Players = game:GetService("Players")
local lines, failed = {}, 0
local function check(ok, label)
	if not ok then failed += 1 end
	table.insert(lines, (ok and "PASS " or "FAIL ") .. label)
end

local camera = workspace.CurrentCamera
check(camera.CameraType == Enum.CameraType.Scriptable, "camera is Scriptable")
check(math.abs(camera.FieldOfView - 20) < 0.01, "camera FOV is 20")

local folder = workspace:FindFirstChild("CrownfallSprites")
check(folder ~= nil, "CrownfallSprites folder exists")
local card = folder and folder:FindFirstChild("SpriteCard")
check(card ~= nil, "a SpriteCard exists")
local gui = card and card:FindFirstChildOfClass("SurfaceGui")
check(gui ~= nil and #gui:GetChildren() > 10, "the card draws pixel runs")

local character = Players.LocalPlayer.Character
local head = character and character:FindFirstChild("Head")
check(head ~= nil and head.Transparency == 1, "the Roblox body is hidden")

if card and character and character:FindFirstChild("HumanoidRootPart") then
	local toCamera = (camera.CFrame.Position - card.Position).Unit
	check(card.CFrame.LookVector:Dot(toCamera) > 0.95, "the card faces the camera")
	local flat = (card.Position - character.HumanoidRootPart.Position) * Vector3.new(1, 0, 1)
	check(flat.Magnitude < 3, "the card stands on the character")
end

table.insert(lines, ("%d failed"):format(failed))
return table.concat(lines, "\n")
```

- [ ] **Step 2: Start Play in Place1, run the check, verify it fails, stop Play**

Start Play with the Studio MCP `start_stop_play` tool (Place1 only), wait about 5 s for the character to spawn, then run:

Run: `python -I Tools/studio.py luau Client @Tools/checks/m1_play.luau`
Expected: `FAIL camera is Scriptable`, `FAIL CrownfallSprites folder exists`, and a non-zero `failed` count. Stop Play before the next step.

- [ ] **Step 3: Write `src/ReplicatedStorage/Crownfall/Render/SpriteCard.luau`**

```lua
-- A camera-facing card that draws one pixel-art frame. Client-side only.
local PixelArt = require(script.Parent.PixelArt)

local PIXEL = 0.25 -- studs per sprite pixel (a 20-pixel hero is 5 studs tall)
local CANVAS_SCALE = 8 -- SurfaceGui pixels per sprite pixel

local SpriteCard = {}
SpriteCard.__index = SpriteCard

function SpriteCard.new(art, parent: Instance)
	local part = Instance.new("Part")
	part.Name = "SpriteCard"
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1
	part.Size = Vector3.new(art.Width * PIXEL, art.Height * PIXEL, 0.05)

	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	gui.CanvasSize = Vector2.new(art.Width * CANVAS_SCALE, art.Height * CANVAS_SCALE)
	gui.LightInfluence = 1
	gui.Parent = part

	part.Parent = parent
	return setmetatable({ part = part, gui = gui, art = art, shown = nil }, SpriteCard)
end

-- Rebuilds the drawing only when the frame actually changes.
function SpriteCard:Show(sheet: string, pose: string, mirror: boolean)
	local key = sheet .. "/" .. pose .. "/" .. tostring(mirror)
	if key == self.shown then
		return
	end
	self.shown = key
	self.gui:ClearAllChildren()
	local art = self.art
	for _, run in ipairs(PixelArt.ToRuns(art.Frame(sheet, pose), mirror)) do
		local f = Instance.new("Frame")
		f.BorderSizePixel = 0
		f.BackgroundColor3 = art.Palette[run.key]
		f.Position = UDim2.fromScale(run.x / art.Width, run.y / art.Height)
		f.Size = UDim2.fromScale(run.w / art.Width, 1 / art.Height)
		f.Parent = self.gui
	end
end

-- Stands the card on `foot`, turned to face the camera so the sprite keeps its full height on screen.
function SpriteCard:Place(foot: Vector3, cameraCFrame: CFrame)
	local cf = CFrame.lookAt(foot, foot - cameraCFrame.LookVector)
	self.part.CFrame = cf + cf.UpVector * (self.part.Size.Y / 2)
end

function SpriteCard:Destroy()
	self.part:Destroy()
end

return SpriteCard
```

- [ ] **Step 4: Write `src/StarterPlayer/StarterPlayerScripts/Crownfall/CameraController.client.luau`**

```lua
-- Fixed three-quarter camera that follows the local character (blueprint: Platform assumption, 4.13).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS.Crownfall.Shared.Config)
local CameraMath = require(RS.Crownfall.Render.CameraMath)

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local offset = CameraMath.Offset(Config.Camera.Pitch, Config.Camera.Distance)
local focus: Vector3? = nil

RunService:BindToRenderStep("CrownfallCamera", Enum.RenderPriority.Camera.Value + 1, function(dt)
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then
		return
	end
	camera.CameraType = Enum.CameraType.Scriptable
	camera.FieldOfView = Config.Camera.FieldOfView
	local target = root.Position
	focus = if focus then focus:Lerp(target, math.min(dt * Config.Camera.FollowSharpness, 1)) else target
	camera.CFrame = CFrame.lookAt(focus + offset, focus)
end)
```

- [ ] **Step 5: Write `src/StarterPlayer/StarterPlayerScripts/Crownfall/CharacterSprites.client.luau`**

```lua
-- Hides every character's Roblox body on this client and draws a 2.5D sprite card in its place.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")

local SpriteCard = require(RS.Crownfall.Render.SpriteCard)
local HeroSprite = require(RS.Crownfall.Render.HeroSprite)
local Facing = require(RS.Crownfall.Render.Facing)
local CameraMath = require(RS.Crownfall.Render.CameraMath)

local RUN_FPS = 8
local MOVING_SPEED = 1 -- studs/s

local camera = workspace.CurrentCamera
local folder = Instance.new("Folder")
folder.Name = "CrownfallSprites"
folder.Parent = workspace

local tracked = {} -- [character Model] = { card, sheet, mirror }

local function hide(inst: Instance)
	if inst:IsA("BasePart") then
		inst.Transparency = 1
	elseif inst:IsA("Decal") then
		inst.Transparency = 1
	end
end

local function untrack(character: Model)
	local t = tracked[character]
	if t then
		t.card:Destroy()
		tracked[character] = nil
	end
end

local function track(character: Model)
	untrack(character)
	for _, d in ipairs(character:GetDescendants()) do
		hide(d)
	end
	character.DescendantAdded:Connect(hide)
	tracked[character] = { card = SpriteCard.new(HeroSprite, folder), sheet = "S", mirror = false }
end

local function watch(player: Player)
	if player.Character then
		track(player.Character)
	end
	player.CharacterAdded:Connect(track)
	player.CharacterRemoving:Connect(untrack)
end

for _, p in ipairs(Players:GetPlayers()) do
	watch(p)
end
Players.PlayerAdded:Connect(watch)

RunService:BindToRenderStep("CrownfallSprites", Enum.RenderPriority.Camera.Value + 2, function()
	local now = os.clock()
	for character, t in pairs(tracked) do
		local root = character.Parent and character:FindFirstChild("HumanoidRootPart")
		local humanoid = character:FindFirstChildOfClass("Humanoid")
		if not root or not humanoid then
			if not character.Parent then
				untrack(character)
			end
			continue
		end
		local velocity = root.AssemblyLinearVelocity * Vector3.new(1, 0, 1)
		local pose = "Idle"
		if velocity.Magnitude > MOVING_SPEED then
			t.sheet, t.mirror = Facing.FromScreen(CameraMath.ToScreen(velocity))
			pose = if math.floor(now * RUN_FPS) % 2 == 0 then "RunA" else "RunB"
		end
		t.card:Show(t.sheet, pose, t.mirror)
		local foot = root.Position - Vector3.new(0, humanoid.HipHeight + root.Size.Y / 2, 0)
		t.card:Place(foot, camera.CFrame)
	end
end)
```

- [ ] **Step 6: Sync, start Play, run the check to verify it passes**

Run: `python -I Tools/studio.py sync && python -I Tools/studio.py test`
Expected: `39 passed, 0 failed` (nothing in the earlier modules broke).

Start Play in Place1, wait about 5 s, then:

Run: `python -I Tools/studio.py luau Client @Tools/checks/m1_play.luau`
Expected: every line `PASS` and `0 failed`.

- [ ] **Step 7: Look at it**

While still in Play, take a `screen_capture` of Place1. Expected: the baseplate seen from a high three-quarter angle, with the placeholder hero (brown hair, lapis cloak, grey armour) standing on it as a flat pixel sprite. Then hold `D` with the Studio MCP `user_keyboard_input` tool for 1 s and capture again. Expected: the side-view sheet with alternating run legs. Stop Play.

- [ ] **Step 8: Commit**

```bash
git add src/ReplicatedStorage/Crownfall/Render/SpriteCard.luau src/StarterPlayer Tools/checks/m1_play.luau
git commit -m "Draw characters as 2.5D sprite cards under a fixed three-quarter camera"
```

### Task 8: Push and report

**Files:**
- Modify: `README.md` (add a "Working on the code" section)

- [ ] **Step 1: Add to `README.md`**

```markdown
## Working on the code

The repo is the source of truth; Studio is a build target. Open the place **Place1** in Studio (Edit mode), then from the repo root:

- `python -I Tools/studio.py sync` pushes `src/` into Place1. It rebuilds every `Crownfall` folder, so never edit those scripts in Studio.
- `python -I Tools/studio.py test` runs every spec in `ServerStorage.Crownfall.Tests`.

Plans for each milestone live in `Docs/Plans/`.
```

- [ ] **Step 2: Commit and push**

```bash
git add README.md
git commit -m "Document the sync and test workflow"
git push
```

- [ ] **Step 3: Report**

Tell the owner: suite result (`39 passed, 0 failed`), the Play check result, and the two screenshots from Task 7, Step 7. M1 is then complete and M2 (Movement) gets its own plan.
