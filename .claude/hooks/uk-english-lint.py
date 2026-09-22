#!/usr/bin/env python3
"""PostToolUse: flag American spellings in prose written to markdown/text files.

Advisory, not blocking — the write has already happened. Exit code 2 hands the
findings back so they get corrected in the same turn.

Code is exempt: fenced blocks, indented blocks, inline code and URLs are stripped
before the scan, so `color: red` or `authorizationToken` never trips it.
"""
import json
import re
import sys

PROSE_SUFFIXES = (".md", ".markdown", ".txt", ".mdx")

# Files that quote American spellings on purpose (this rule's own documentation).
EXEMPT_PATHS = (
    "/.claude/skills/plain-uk-english/",
    "/.claude/hooks/",
)

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
    "maize", "assize", "authorized_keys",
}

BANNED_JARGON = [
    "seamless", "robust", "leverage", "synergy", "holistic", "best-in-class",
    "touch base", "circle back", "going forward", "at your earliest convenience",
    "please be advised", "utilize", "utilise",
]


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"^(?: {4}|\t).*$", " ", text, flags=re.M)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", text)
    return text


def findings(text: str):
    prose = strip_code(text)
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

    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not path.lower().endswith(PROSE_SUFFIXES):
        return 0
    normalised = path.replace("\\", "/")
    if any(part in normalised for part in EXEMPT_PATHS):
        return 0

    written = " ".join(
        str(tool_input.get(k, ""))
        for k in ("content", "new_string", "new_str")
    )
    for edit in tool_input.get("edits") or []:
        written += " " + str(edit.get("new_string", ""))
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
