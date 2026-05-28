#!/usr/bin/env python3
"""Audit hook — logs all tool uses. Blocks known dangerous patterns."""
import json
import sys
from datetime import datetime

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = payload.get("tool_name", "")
inp = payload.get("tool_input", {})
cmd = inp.get("command", "")

BLOCKED = ["rm -rf /", "git push --force", "DROP TABLE", "DELETE FROM"]
for b in BLOCKED:
    if b in cmd:
        print(json.dumps({"decision": "block", "reason": f"Blocked pattern: {b}"}))
        sys.exit(0)

with open(".claude/tool_audit.log", "a") as f:
    f.write(f"{datetime.utcnow().isoformat()} | {tool} | {cmd[:120]}\n")
