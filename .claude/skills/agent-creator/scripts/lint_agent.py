#!/usr/bin/env python3
"""Mechanical gate check for a Claude Code subagent file (.claude/agents/<name>.md).

Covers what a script can decide. Judgement gates (single responsibility, whether a
vague word is defined, whether the description would mis-delegate) stay with the
reviewer; this script flags candidates for them as CHECK.

Levels:
  FAIL  - gate fails; fix before testing
  CHECK - reviewer must look and decide; record the decision
  WARN  - likely problem; fix or justify

Usage: lint_agent.py <agent.md> [--json]
Exit code 1 if any FAIL.
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
KNOWN_TOOLS = {
    "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "Bash", "PowerShell",
    "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite", "Skill", "LSP", "Monitor",
    "ToolSearch", "TaskStop", "SendMessage", "EnterWorktree", "ExitWorktree", "Artifact",
}
# Stripped from every subagent by Claude Code, so listing them does nothing.
SUBAGENT_STRIPPED = {"AskUserQuestion", "EndConversation", "EnterPlanMode", "ExitPlanMode",
                     "ScheduleWakeup", "Workflow", "WaitForMcpServers"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
EXEC_TOOLS = {"Bash", "PowerShell"}
KNOWN_KEYS = {"name", "description", "tools", "disallowedTools", "model", "permissionMode",
              "maxTurns", "skills", "mcpServers", "hooks", "memory", "background",
              "omitClaudeMd", "effort", "isolation", "color", "initialPrompt", "experimental"}
MODEL_ALIASES = {"sonnet", "opus", "haiku", "fable", "inherit"}
VAGUE = ["properly", "as needed", "as necessary", "appropriately", "appropriate",
         "if needed", "where relevant", "relevant", "etc", "and so on", "best practices",
         "correctly", "reasonable", "sensible", "thoroughly", "robust", "clean up",
         "handle", "make sure it works", "good quality", "as required", "when necessary"]
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|XXX|lorem ipsum)\b|\{\{.*?\}\}|<(your|agent|insert|placeholder|name|description)[^>]*>|\[(insert|todo|tbd|placeholder)[^\]]*\]",
    re.IGNORECASE)
TRIGGER_RE = re.compile(r"\b(use (it |this |this agent )?(when|for|after|before|as|to|proactively|whenever)|use proactively|delegate)\b", re.IGNORECASE)
NEGATIVE_RE = re.compile(r"\b(not for|never|do not use|don't use|does not|doesn't|only)\b", re.IGNORECASE)
SECTION_PATTERNS = {
    "output contract": re.compile(r"^#{1,4}\s*.*\b(output|return|report|response)\b", re.IGNORECASE | re.MULTILINE),
    "failure handling": re.compile(r"^#{1,4}\s*.*\b(fail|stop|block|missing|ambigu|out of scope|when (you )?can(no|')t|escalat)", re.IGNORECASE | re.MULTILINE),
    "boundaries": re.compile(r"^#{1,4}\s*.*\b(boundar|must not|never|limit|do not|don't|out of scope|constraint|hard rule|rules)", re.IGNORECASE | re.MULTILINE),
}


def split_frontmatter(text):
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, text
    end = re.search(r"^---\s*$", text[4:], re.MULTILINE)
    if not end:
        return None, text
    return text[4:4 + end.start()], text[4 + end.end():]


def parse_tools(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [t.strip() for t in str(value).split(",") if t.strip()]


def lint(path):
    findings = []

    def add(level, gate, msg):
        findings.append({"level": level, "gate": gate, "message": msg})

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        add("FAIL", "format", "No YAML frontmatter: file must start with '---' on line 1. Claude Code silently skips it.")
        return findings, {}
    try:
        fm = yaml.safe_load(fm_text) if yaml else {}
    except Exception as e:  # noqa: BLE001
        add("FAIL", "format", f"YAML parse error (Claude Code silently skips the file): {e}")
        return findings, {}
    if not isinstance(fm, dict):
        add("FAIL", "format", "Frontmatter is not a mapping.")
        return findings, {}

    for key in fm:
        if key not in KNOWN_KEYS:
            add("WARN", "format", f"Unknown frontmatter key '{key}' (typo? check the docs).")

    # Naming
    name = fm.get("name")
    if not name:
        add("FAIL", "naming", "Missing 'name'. Claude Code treats the file as documentation, not an agent.")
    else:
        name = str(name)
        if not NAME_RE.match(name):
            add("FAIL", "naming", f"name '{name}' is not lowercase-hyphenated (a-z, 0-9, single hyphens).")
        if name != p.stem:
            add("FAIL", "naming", f"name '{name}' does not match file name '{p.stem}.md'.")
        if len(name.split("-")) == 1 and name in {"helper", "agent", "assistant", "worker", "bot", "utility", "tool"}:
            add("FAIL", "naming", f"name '{name}' does not describe a job.")

    # Description
    desc = str(fm.get("description") or "").strip()
    if not desc:
        add("FAIL", "description", "Missing 'description'. Claude Code skips the agent.")
    else:
        words = len(desc.split())
        if words < 15:
            add("FAIL", "description", f"Description is {words} words; too thin to say WHAT and WHEN.")
        if words > 120:
            add("WARN", "description", f"Description is {words} words; move detail into the body (descriptions load for every session).")
        if not TRIGGER_RE.search(desc):
            add("FAIL", "description", "Description has no WHEN clause (e.g. 'Use when…', 'Use for…', 'Use proactively after…').")
        if not NEGATIVE_RE.search(desc):
            add("CHECK", "description", "Description says nothing about what it does NOT do. Confirm it cannot be picked by accident for a near-miss task.")
        if not re.search(r"[\"'“‘]", desc):
            add("CHECK", "description", "No quoted trigger phrases. Confirm the WHEN clause names concrete user phrasings or situations.")

    # Tools
    tools = parse_tools(fm.get("tools"))
    if tools is None:
        add("FAIL", "least-privilege", "No 'tools' field: the agent inherits EVERY tool, including Write, Edit and Bash. List only what the job needs.")
        tools = []
    elif not tools:
        add("FAIL", "least-privilege", "'tools' is empty; the agent will fail to launch with zero tools.")
    for t in tools:
        base = t.split("(")[0]
        if base == "*":
            add("FAIL", "least-privilege", "'*' grants every tool.")
        elif base in SUBAGENT_STRIPPED:
            add("FAIL", "least-privilege", f"'{base}' is removed from every subagent; listing it does nothing. Failure handling must report back, not ask the user.")
        elif base == "Agent":
            add("FAIL", "single-responsibility", "'Agent' lets the subagent spawn others; subagents cannot nest. Remove it.")
        elif base.startswith("mcp__"):
            if base.endswith("__*") or base.count("__") == 1:
                add("WARN", "least-privilege", f"'{base}' grants a whole MCP server. Name the exact tools if the job needs only some.")
        elif base not in KNOWN_TOOLS:
            add("WARN", "format", f"Unknown tool '{base}' (typo? it will not resolve).")
    granted = {t.split("(")[0] for t in tools}
    for t in sorted(granted & WRITE_TOOLS):
        add("CHECK", "least-privilege", f"'{t}' can change files. Justify it against the job, or remove it.")
    for t in sorted(granted & EXEC_TOOLS):
        add("CHECK", "least-privilege", f"'{t}' can run any command, including ones that write. Justify it and state in Boundaries which commands are allowed.")
    if "Write" in granted and "Edit" in granted:
        add("CHECK", "least-privilege", "Both Write and Edit granted. If the agent only changes existing files, drop Write.")
    if fm.get("permissionMode") in ("bypassPermissions", "dontAsk", "auto"):
        add("FAIL", "least-privilege", f"permissionMode '{fm.get('permissionMode')}' removes the human check. Needs an explicit, recorded reason.")

    model = fm.get("model")
    if model is not None and str(model) not in MODEL_ALIASES and not str(model).startswith("claude-"):
        add("FAIL", "format", f"model '{model}' is not an alias (sonnet, opus, haiku, fable, inherit) or a claude-* model ID.")

    # Body
    stripped = body.strip()
    if len(stripped.split()) < 60:
        add("FAIL", "clear-instructions", "System prompt body is under 60 words; too thin to define steps, output and limits.")
    if not re.search(r"^\s*1\.\s", body, re.MULTILINE):
        add("FAIL", "clear-instructions", "No numbered steps ('1. …') in the body.")
    for gate, pat in SECTION_PATTERNS.items():
        if not pat.search(body):
            add("FAIL", gate.replace(" ", "-"), f"No heading for {gate}. Give it its own section so it can be found and checked.")

    # Output contract needs a concrete shape
    if SECTION_PATTERNS["output contract"].search(body) and "```" not in body:
        add("CHECK", "output-contract", "No fenced template in the body. Confirm the output section fixes structure, section names and length.")

    # Vague words (candidates only: a vague word followed by its definition is fine)
    for line_no, line in enumerate(body.splitlines(), start=1 + text[:len(text) - len(body)].count("\n")):
        low = line.lower()
        for w in VAGUE:
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low):
                add("CHECK", "clear-instructions", f"line {line_no}: vague word '{w}': \"{line.strip()[:100]}\". Keep only if the same sentence says exactly what it means.")

    # Placeholders
    for m in PLACEHOLDER_RE.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        add("FAIL", "no-placeholders", f"line {line_no}: placeholder text '{m.group(0)}'.")

    # Duplicated instructions (identical substantive lines)
    seen = {}
    for line_no, line in enumerate(body.splitlines(), 1):
        key = re.sub(r"^[\s>*\-\d.]+", "", line).strip().lower()
        if len(key) >= 40:
            if key in seen:
                add("WARN", "no-duplication", f"Line repeated (body lines {seen[key]} and {line_no}): \"{key[:80]}\".")
            else:
                seen[key] = line_no

    return findings, {"name": name, "tools": tools, "model": model, "body_words": len(stripped.split())}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    findings, meta = lint(args[0])
    fails = [f for f in findings if f["level"] == "FAIL"]
    if "--json" in sys.argv:
        print(json.dumps({"file": args[0], "meta": meta, "findings": findings,
                          "passed": not fails}, indent=2))
    else:
        order = {"FAIL": 0, "CHECK": 1, "WARN": 2}
        for f in sorted(findings, key=lambda f: order[f["level"]]):
            print(f"{f['level']:5}  [{f['gate']}] {f['message']}")
        counts = {lvl: sum(f["level"] == lvl for f in findings) for lvl in order}
        print(f"\n{counts['FAIL']} FAIL, {counts['CHECK']} CHECK, {counts['WARN']} WARN"
              f" -> {'mechanical gates PASS' if not fails else 'mechanical gates FAIL'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
