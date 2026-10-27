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
