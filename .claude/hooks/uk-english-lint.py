#!/usr/bin/env python3
"""PostToolUse: flag American spellings in prose written to markdown/text files.

Advisory, not blocking — the write has already happened. Exit code 2 hands the
findings back so they get corrected in the same turn.

Only the text just written is scanned: `content` on Write, `new_string` on Edit and
MultiEdit. Old text elsewhere in the file is never re-reported.

Scope: workspace-owned prose only — root-level files and anything under `.claude/`,
`.work/` or `docs/`. Files inside a product repo or any nested git checkout
(fk-admin-panel-be/, a ticket worktree under .work/) belong to other teams and are
skipped.

Not prose, so stripped before the scan: fenced, indented and inline code, URLs,
links, YAML frontmatter, HTML comments, blockquote lines and quoted strings. Words
that look like code are skipped too: camelCase, ALL_CAPS, and anything holding
`_ . ( /` — so `normalizeDate()`, `sanitize.js` and `CANCELED` never trip it.
"""
import json
import os
import re
import sys

PROSE_SUFFIXES = (".md", ".markdown", ".txt", ".mdx")

# Files that quote American spellings on purpose (this rule's own documentation).
EXEMPT_PATHS = (
    "/.claude/skills/plain-uk-english/",
    "/.claude/hooks/",
)

# Top-level folders of the workspace whose prose is ours. Root-level files count too.
SCANNED_DIRS = (".claude", ".work", "docs")

# American -> British. Only pairs that are unambiguous in prose.
SWAPS = {
    r"\b(\w*)ize\b": "-ise",
    r"\b(\w*)ized\b": "-ised",
    r"\b(\w*)izes\b": "-ises",
    r"\b(\w*)izing\b": "-ising",
    r"\b(\w*)ization\b": "-isation",
    r"\bcolor(s|ed|ing)?\b": "colour",
    r"\bbehavior(s|al)?\b": "behaviour",
    r"\bfavor(s|ed|ite|ites)?\b": "favour",
    r"\blabor\b": "labour",
    r"\bcenter(s|ed|ing)?\b": "centre",
    r"\bfiber(s)?\b": "fibre",
    r"\bcatalog(s|ed)?\b": "catalogue",
    r"\bdialog(s)?\b": "dialogue",
    r"\banalog\b": "analogue",
    r"\bcancel(ed|ing)\b": "cancelled / cancelling",
    r"\bmodel(ed|ing)\b": "modelled / modelling",
    r"\btravel(ed|ing)\b": "travelled / travelling",
    r"\blabel(ed|ing)\b": "labelled / labelling",
    r"\bdefense\b": "defence",
    r"\boffense\b": "offence",
    r"\bpretense\b": "pretence",
    r"\banalyz(e|ed|es|ing|er|ers)\b": "analyse / analyser",
    r"\bparalyz(e|ed|es|ing)\b": "paralyse",
    r"\benrollment\b": "enrolment",
    r"\bfulfill(s|ed|ing|ment)?\b": "fulfil",
    r"\bskillful\b": "skilful",
    r"\bgray\b": "grey",
}

# Words that end in -ize/-ise but are not the American form, or are proper nouns.
ALLOW = {
    "size", "sizes", "sized", "sizing", "prize", "prizes", "seize", "seizes",
    "capsize", "resize", "resized", "resizes", "resizing", "downsize", "upsize",
    "maize", "assize", "authorized_keys", "citizen", "citizens",
}

BANNED_JARGON = [
    "seamless", "robust", "leverage", "synergy", "holistic", "best-in-class",
    "touch base", "circle back", "going forward", "at your earliest convenience",
    "please be advised", "utilize", "utilise",
]

LEAD_STRIP = "([{\"'*_“‘"
TRAIL_STRIP = ".,;:!?)]}\"'*_”’"


def project_root() -> str:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return os.path.abspath(env)
    # <root>/.claude/hooks/uk-english-lint.py
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def in_scope(path: str, root: str) -> bool:
    """Is this file workspace-owned prose we should check?"""
    full = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    rel = os.path.relpath(full, root).replace("\\", "/")
    if rel.startswith("../") or rel == "..":
        return False
    parts = rel.split("/")
    if len(parts) > 1 and parts[0] not in SCANNED_DIRS:
        return False
    # Any nested git checkout between the file and the root is another repo or a
    # ticket worktree of one — not our prose.
    d = os.path.dirname(full)
    while d.startswith(root) and d != root:
        if os.path.exists(os.path.join(d, ".git")):
            return False
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return True


def strip_non_prose(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---[ \t]*(\n|\Z)", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"^(?: {4}|\t).*$", " ", text, flags=re.M)
    text = re.sub(r"^[ \t]*>.*$", " ", text, flags=re.M)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(r"“[^”\n]*”", " ", text)
    text = re.sub(r"(?<![\w])'[^'\n]+'(?![\w])", " ", text)
    text = re.sub(r"(?<![\w])‘[^’\n]+’(?![\w])", " ", text)
    return text


def looks_like_code(word: str) -> bool:
    if any(c in word for c in "_.(/"):
        return True
    if re.search(r"[a-z][A-Z]", word):
        return True  # camelCase / PascalCase with an inner capital
    letters = re.sub(r"[^A-Za-z]", "", word)
    return len(letters) >= 2 and letters.isupper()  # ALL_CAPS / enum value


def prose_words(text: str) -> str:
    kept = []
    for chunk in strip_non_prose(text).split():
        word = chunk.lstrip(LEAD_STRIP).rstrip(TRAIL_STRIP)
        if not word or looks_like_code(word):
            continue
        kept.append(word)
    return " ".join(kept)


def findings(text: str):
    prose = prose_words(text)
    hits = []
    for pattern, british in SWAPS.items():
        for m in re.finditer(pattern, prose, flags=re.I):
            word = m.group(0)
            if word.lower() in ALLOW:
                continue
            hits.append(f"{word} -> {british}")
    for term in BANNED_JARGON:
        if re.search(rf"\b{re.escape(term)}\b", prose, flags=re.I):
            hits.append(f'"{term}" -> plain word')
    seen, out = set(), []
    for h in hits:
        key = h.lower()
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:15]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not path.lower().endswith(PROSE_SUFFIXES):
        return 0
    normalised = path.replace("\\", "/")
    if any(part in normalised for part in EXEMPT_PATHS):
        return 0
    if not in_scope(path, project_root()):
        return 0

    written = "\n".join(
        str(tool_input.get(k, ""))
        for k in ("content", "new_string", "new_str")
        if tool_input.get(k)
    )
    for edit in tool_input.get("edits") or []:
        written += "\n" + str(edit.get("new_string", ""))
    if not written.strip():
        return 0

    hits = findings(written)
    if not hits:
        return 0

    print(
        f"UK English check on {path} — fix these in the file now:\n  "
        + "\n  ".join(hits)
        + "\nCode identifiers, API fields and quoted errors are exempt; prose is not.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
