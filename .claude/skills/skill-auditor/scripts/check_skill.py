#!/usr/bin/env python3
"""Mechanical checks for one skill directory (the folder holding SKILL.md).

Decides what a script can decide. Judgement items (intent match, whether a vague
word is defined in the same sentence, whether two skills truly overlap) are
flagged as CHECK for the auditor to decide and record.

Levels:
  FAIL  - broken; the skill cannot be APPROVED until fixed
  WARN  - likely problem; fix or record why it is fine
  CHECK - auditor must look and decide
  PASS  - mechanical check passed

Usage:
  check_skill.py <skill-dir>                 # checks
  check_skill.py <skill-dir> --neighbours [--intent "<confirmed intent>"]
      also list other installed skills ranked by word overlap with the skill's
      description and, if given, the confirmed intent (a bad description hides
      neighbours, so pass the intent whenever you have it)
Exit code 1 if any FAIL, 2 if the path is not a skill directory.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Agent Skills spec keys plus the extra keys Claude Code reads.
KNOWN_KEYS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
    "argument-hint", "disable-model-invocation", "user-invocable", "model", "context",
    "agent", "hooks", "when_to_use", "version", "effort", "paths", "shell",
}
VAGUE = ["as needed", "as necessary", "appropriately", "as appropriate", "properly",
         "if needed", "if necessary", "where relevant", "when relevant", "etc.",
         "and so on", "best practices", "handle it", "handle appropriately",
         "make sure it works", "as required", "when necessary", "reasonable",
         "sensible", "robust"]
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|XXX|lorem ipsum)\b|\{\{.*?\}\}|\[(insert|todo|tbd|placeholder)[^\]]*\]",
    re.IGNORECASE)
WHEN_RE = re.compile(r"\b(use (this |it )?(when|whenever|for|after|before|to)|trigger|whenever)\b", re.I)
NOT_RE = re.compile(r"\b(not for|do not use|don't use|never|not when|instead use|use .* instead)\b", re.I)
EXAMPLE_RE = re.compile(r"^#{1,4}\s.*\bexample", re.I | re.M)
EDGE_RE = re.compile(r"\b(if (the )?\S+ (is )?(missing|empty|absent|not found|does not exist)|edge case|fails?|failure|stop and)\b", re.I)
REF_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|agents|evals|templates)/[\w./-]+\w)")
STOP_WORDS = set("a an the and or of to for in on with when use this skill skills is are be it "
                 "that any you your from by as at not do does into its user users".split())

results = []


def emit(level, item, msg):
    results.append((level, item, msg))


def split_frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\s*(\r?\n|$)", text, re.S)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def check(skill_dir: Path):
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)

    # Frontmatter
    fm = {}
    if fm_text is None:
        emit("FAIL", "frontmatter", "no YAML frontmatter between --- lines at top of SKILL.md")
    elif yaml is None:
        emit("CHECK", "frontmatter", "PyYAML missing; parse the frontmatter by eye")
    else:
        try:
            fm = yaml.safe_load(fm_text) or {}
            if not isinstance(fm, dict):
                emit("FAIL", "frontmatter", "frontmatter is not a YAML mapping")
                fm = {}
        except yaml.YAMLError as e:
            emit("FAIL", "frontmatter", f"invalid YAML: {str(e).splitlines()[0]}")

    name = fm.get("name")
    if fm_text is not None and fm:
        if not isinstance(name, str) or not name.strip():
            emit("FAIL", "frontmatter", "name missing or empty")
        elif not NAME_RE.match(name) or len(name) > 64:
            emit("FAIL", "frontmatter", f"name '{name}' must be kebab-case, max 64 chars")
        elif name != skill_dir.name:
            emit("WARN", "frontmatter", f"name '{name}' differs from folder '{skill_dir.name}'")
        else:
            emit("PASS", "frontmatter", f"name '{name}' valid and matches folder")
        unknown = set(fm) - KNOWN_KEYS
        if unknown:
            emit("WARN", "frontmatter", f"unknown keys: {', '.join(sorted(unknown))}")

    desc = fm.get("description")
    if fm_text is not None and fm:
        if not isinstance(desc, str) or not desc.strip():
            emit("FAIL", "frontmatter", "description missing or empty")
            desc = ""
        else:
            desc = desc.strip()
            if len(desc) > 1024:
                emit("FAIL", "frontmatter", f"description {len(desc)} chars; max 1024")
            if "<" in desc or ">" in desc:
                emit("WARN", "frontmatter", "description contains < or >; Claude Code loads it, but skill-creator packaging and claude.ai upload reject it")
            words = len(desc.split())
            if words < 15:
                emit("WARN", "triggering", f"description only {words} words; likely too thin to trigger")
            emit("PASS" if WHEN_RE.search(desc) else "FAIL", "triggering",
                 "description says when to use" if WHEN_RE.search(desc)
                 else "description has no 'use when/whenever/for' clause")
            emit("PASS" if NOT_RE.search(desc) else "WARN", "triggering",
                 "description has a not-for clause" if NOT_RE.search(desc)
                 else "description has no not-for clause; check near-miss false triggers")
    else:
        desc = desc or ""

    # Body
    lines = text.count("\n") + 1
    if lines > 500:
        emit("WARN", "length", f"SKILL.md is {lines} lines; over 500, move detail to references/")
    else:
        emit("PASS", "length", f"SKILL.md is {lines} lines")
    if not body.strip():
        emit("FAIL", "instructions", "SKILL.md has no body")

    for ph in {m.group(0) for m in PLACEHOLDER_RE.finditer(text)}:
        emit("FAIL", "consistency", f"placeholder text left in: '{ph}'")

    body_lower = body.lower()
    for v in VAGUE:
        for m in re.finditer(r"(?<!\w)" + re.escape(v) + r"(?!\w)", body_lower):
            line_no = body[:m.start()].count("\n") + 1 + (text.count("\n", 0, len(text) - len(body)))
            emit("CHECK", "instructions", f"vague phrase '{v}' at SKILL.md:{line_no}; is the rule stated in the same sentence?")

    emit("PASS" if EXAMPLE_RE.search(body) else "WARN", "examples",
         "has an Example heading" if EXAMPLE_RE.search(body) else "no heading containing 'example'; look for an inline one")
    emit("PASS" if EDGE_RE.search(body) else "WARN", "edge-cases",
         "mentions missing/failure paths" if EDGE_RE.search(body) else "no missing-input or failure wording found")

    # File structure
    all_text = text
    bundled = [p for p in skill_dir.rglob("*") if p.is_file()
               and "__pycache__" not in p.parts and p.name != "SKILL.md"
               and not any(part.startswith(".") for part in p.relative_to(skill_dir).parts)]
    for p in bundled:
        if p.suffix in {".md", ".py", ".sh", ".txt", ".json", ".yaml", ".yml", ".js", ".ts"}:
            try:
                all_text += "\n" + p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pass
    refs = sorted(set(REF_RE.findall(text)))
    missing = [r for r in refs if not (skill_dir / r).exists() and "<" not in r and "*" not in r]
    for r in missing:
        emit("FAIL", "file-structure", f"SKILL.md references '{r}' but it does not exist")
    if refs and not missing:
        emit("PASS", "file-structure", f"all {len(refs)} referenced paths exist")
    for p in bundled:
        rel = p.relative_to(skill_dir).as_posix()
        if rel.startswith("evals/"):
            continue
        if p.name not in all_text and rel not in all_text:
            emit("WARN", "file-structure", f"'{rel}' is not referenced anywhere; unused leftover?")
    for p in skill_dir.rglob("__pycache__"):
        emit("WARN", "file-structure", f"'{p.relative_to(skill_dir)}' is build clutter; delete it")

    return (name if isinstance(name, str) else skill_dir.name), desc


def skill_roots(skill_dir: Path):
    home = Path.home()
    roots = [home / ".claude" / "skills"]
    for start in (skill_dir.resolve(), Path.cwd().resolve()):
        for d in (start, *start.parents):
            if (d / ".claude" / "skills").is_dir():
                roots.append(d / ".claude" / "skills")
    roots += list((home / ".claude" / "plugins" / "cache").glob("*/*/*/skills"))
    out = []
    for r in roots:
        if r.is_dir() and r.resolve() not in [o.resolve() for o in out]:
            out.append(r)
    return out


def tokens(s):
    return {w for w in re.findall(r"[a-z][a-z-]{2,}", s.lower()) if w not in STOP_WORDS}


def neighbours(skill_dir: Path, name: str, desc: str, intent: str):
    mine, wanted = tokens(desc), tokens(intent)
    seen, rows = set(), []
    for root in skill_roots(skill_dir):
        for md in root.glob("*/SKILL.md"):
            if md.parent.resolve() == skill_dir.resolve():
                continue
            fm_text, _ = split_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
            try:
                fm = (yaml.safe_load(fm_text) if yaml and fm_text else {}) or {}
            except Exception:
                fm = {}
            other = str(fm.get("name", md.parent.name))
            other_desc = str(fm.get("description", ""))
            key = (other, other_desc[:80])
            if key in seen:
                continue
            seen.add(key)
            theirs = tokens(other_desc)
            score = max(len(t & theirs) / max(1, len(t | theirs)) for t in (mine, wanted) if t) if (mine or wanted) else 0
            rows.append((score, other, md.parent, other_desc))
            if other == name:
                emit("FAIL", "scope", f"another skill is also named '{name}': {md.parent}")
    rows.sort(key=lambda r: -r[0])
    print("\nNEIGHBOURS (top 8 by word overlap with description" + (" or intent" if intent else "") + "; read the close ones before judging Scope)")
    for score, other, path, other_desc in rows[:8]:
        print(f"  {score:.2f}  {other}  {path}\n        {other_desc[:220]}")


def main():
    argv = sys.argv[1:]
    intent = ""
    if "--intent" in argv:
        i = argv.index("--intent")
        intent = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    skill_dir = Path(args[0]).expanduser()
    if skill_dir.name == "SKILL.md":
        skill_dir = skill_dir.parent
    if not (skill_dir / "SKILL.md").is_file():
        print(f"BLOCKED: no SKILL.md in {skill_dir}")
        sys.exit(2)
    name, desc = check(skill_dir)
    if "--neighbours" in sys.argv:
        neighbours(skill_dir, name, desc, intent)
    print()
    order = {"FAIL": 0, "WARN": 1, "CHECK": 2, "PASS": 3}
    for level, item, msg in sorted(results, key=lambda r: order[r[0]]):
        print(f"{level:5}  {item:14} {msg}")
    fails = sum(1 for r in results if r[0] == "FAIL")
    print(f"\n{fails} FAIL, {sum(1 for r in results if r[0] == 'WARN')} WARN, "
          f"{sum(1 for r in results if r[0] == 'CHECK')} CHECK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
