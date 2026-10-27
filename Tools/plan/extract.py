"""Write the code blocks of a plan file to disk. python Tools/plan/extract.py <plan.md> <path-prefix-or-exact>..."""
import os, re, sys
plan = open(sys.argv[1], encoding="utf-8").read()
blocks = re.findall(r"\*\*Step \d+: Write (?:the failing (?:spec|Play check) )?`([^`]+)`\*\*\n\n```\w+\n(.*?)```", plan, re.S)
wanted = sys.argv[2:]
for path, code in blocks:
    if any(path == w or path.startswith(w) for w in wanted):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        open(path, "w", encoding="utf-8", newline="\n").write(code)
        print("wrote", path, len(code))
