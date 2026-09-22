---
name: plain-uk-english
description: Write every word that reaches a human in British English and plain, short sentences — answers in chat, Jira tickets, PR titles and descriptions, commit messages, code comments, docs and reports. Use whenever text is written for a person to read, and especially when the draft is long, formal or full of jargon. Owns spelling, sentence length, word choice and answer shape; does not own any document's template, evidence rules or gates.
---

# Plain UK English

Two rules, always on:

1. **British spelling and dates.** Not American.
2. **Plain, short, direct.** Say the thing. Stop.

The reader is a colleague who is busy, not a fool. Short does not mean vague.

## 1. British spelling

| Write | Not |
|---|---|
| organise, authorise, prioritise, synchronise | organize, authorize, … |
| colour, behaviour, favour, labour | color, behavior, … |
| licence (noun), practice (noun) / practise (verb) | license, practice |
| centre, metre, fibre | center, meter, fiber |
| catalogue, dialogue, analogue | catalog, dialog, analog |
| cancelled, modelling, travelled, labelled | canceled, modeling, … |
| defence, offence, pretence | defense, offense, pretense |
| grey, cheque, storey, whilst-free plain "while" | gray, check (bank), story (floor) |
| analyse, paralyse | analyze, paralyze |
| enrolment, fulfil, skilful | enrollment, fulfill, skillful |

Dates: `21 September 2026` or `2026-09-21`. Never `09/21/2026`.
Money: `£1,250.00`. Time: 24-hour where it avoids doubt.

**Exception — code stays as it is.** Identifiers, API fields, DB columns, CSS
(`color`, `center`), library names, third-party labels and existing product UI text keep
their original spelling. Never rename `authorizationToken` to `authorisationToken` to
satisfy this skill. UK spelling applies to prose, not to symbols.

## 2. Plain words

| Write | Not |
|---|---|
| use | utilise, leverage |
| start / end | commence, terminate, initiate |
| about | with regard to, in relation to, regarding |
| now | at this point in time, currently |
| so / because | therefore, consequently, as such |
| help | facilitate, enable |
| change | modification, amendment |
| need | requirement to, necessitate |
| also | additionally, furthermore, moreover |
| but | however, nevertheless |
| ask | request, reach out to |
| let you know | keep you apprised |

Ban outright: *seamless, robust, leverage, synergy, holistic, best-in-class,
touch base, circle back, going forward, at your earliest convenience, please be advised*.

Keep exact technical terms: `resolver`, `migration`, `mutation`, `worktree`, `GraphQL`,
error strings, file paths, commands. Precision beats simplicity when they clash.

## 3. Sentence shape

- One idea per sentence. Aim under 20 words.
- Active voice: "the resolver rejects the order", not "the order is rejected by the resolver".
- No sentence that only introduces another sentence.
- Bullets for lists of things. Prose for reasoning. Never bullets of one word each.
- No headings on a three-line answer.

## 4. Answer shape

Answer first. Detail after. Only if asked.

```
[The answer]. [Why, one line]. [What to do next, if anything.]
```

Cut on sight:

- Openers: "Great question", "Sure", "I'd be happy to", "Let me explain".
- Closers: "Let me know if you need anything else", "Hope this helps".
- Restating the question back before answering it.
- Listing what you will not do, or options you already rejected.
- Apologies for things that need no apology.
- Summaries of a summary.

If the answer is yes, the answer is "Yes." plus the reason. Not three paragraphs
ending in yes.

## 5. Where this applies

| Surface | Applies |
|---|---|
| Chat answers to the user | Yes |
| Jira tickets, acceptance criteria | Yes — with `business-requirement-writing-style` for structure |
| PR title and description | Yes — with `pull-request` |
| Commit messages | Yes — one line, see the repo rule |
| Docs, reports, `docs/**` | Yes |
| Code comments | Yes |
| Code identifiers, API fields, DB columns | **No** — never rewrite a symbol |
| Quoted error text, logs, third-party UI labels | **No** — quote verbatim |

## 6. Self-check before sending

- Any American spelling in prose? Fix it.
- First sentence — does it answer, or warm up? Cut the warm-up.
- Any sentence over 25 words? Split it.
- Any word from the ban list? Swap it.
- Could a sentence be deleted with nothing lost? Delete it.
