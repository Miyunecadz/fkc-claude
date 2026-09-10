---
name: screenshot-requirement-analysis
description: Read screenshots, photos of screens, mockups and annotated images supplied with a request as requirement evidence — page and section, tabs, field labels and values, required markers, controls, table columns and their order, filters and sorts, pagination, empty/error/validation states, toasts, dates and currency formats, roles, environment hints, arrows and mark-ups, before/after pairs — inventory every readable element so none is left out, and judge correctly whether several images are one requirement seen from different angles or genuinely separate asks. Use whenever images accompany a feature request, bug report, ticket, spec or design brief, and especially when the written text is short: images carrying most of the requirement is the common case, not an edge case. Produces the image evidence rows other skills consume; does not classify, gate or write the deliverable.
---

# Screenshot requirement analysis

Images supplied with a request are requirement evidence, not decoration attached to the
text. Treat them with the same rigour as the words — and with more suspicion, because a
screenshot shows a hundred things at once and only some of them are the requirement.

Your output is an **inventory**: one row per readable element that could bear on the
request, ready for the `requirement-evidence-and-gating` skill to tag `VISUAL` and
disposition. You do not decide whether the deliverable gets written.

## 1. Inspect every image, and say how many there were

Count them, list them, and work through all of them before drawing any conclusion. Two
common and costly slips:

- reading the first image and treating the rest as more of the same;
- skipping an image because the accompanying text was short — **short text plus images is
  the normal pattern, not a hint that the images are secondary.** The text is often only a
  pointer at them.

Name images the way the requester does ("the first screenshot", "the one with the red
box") as well as by number, so questions and the deliverable refer to the same thing they
do.

## 2. Extraction checklist — walk it per image

Work the whole list each time. Anything genuinely readable and relevant becomes a row;
anything illegible goes to §5. Do not stop at the element you were looking for — the
element you were not looking for is where the missed requirement usually hides.

**Where you are**

- product area, page or screen name, breadcrumb, route or URL fragment, window title;
- section, panel, card, or step of a wizard;
- tabs — which exist, which one is active;
- modal vs full page; side panel vs inline;
- device and form factor: web browser chrome, mobile frame, tablet, print preview.

**What is on it**

- every field label, and its value as shown;
- required/optional markers, helper text, placeholder text, character counters;
- dropdowns: the selected value, and any options visible in an open list;
- tick boxes and radios, with their checked state;
- buttons, links, icon controls, menus — their exact labels;
- table columns, **in the order shown**, plus which are sorted and which direction;
- rows visible, totals, row counts, "showing x of y", pagination controls;
- filters and search terms currently applied — this bounds the data the requirement is
  about, and is the single most commonly missed element on the list;
- badges, chips, status labels, colour-coded states (say what the colour marks, not just
  that it is coloured).

**What state it is in**

- empty state, loading state, disabled controls, read-only fields;
- validation messages, inline errors, error pages, toasts, banners, confirmation dialogs;
- permissions on show: who is logged in, role indicator, user menu, tenant or company
  selector.

**Formats and values worth copying exactly**

- date and time formats, currency symbols and decimal places, number grouping, units;
- identifiers, reference numbers, codes and their shape;
- language and locale, including spelling variants visible in the product's own labels.

**Environment hints**

- host or environment in a URL, environment banner, version string, build number, seeded
  or obviously test data.

Environment matters because "does this already work" has no answer until you know which
environment the image came from. Report the hint; the calling skill decides what to do
with it.

**Annotations — the requester's own commentary**

- arrows, circles, red boxes, highlighter, crossings-out, handwriting, numbered call-outs,
  cropped-in insets, blurred or redacted regions.

An annotation is `EXPLICIT`-strength intent expressed in an image: it says *this part is
the point*. Never treat a marked-up region as ordinary screen content, and never ignore an
arrow because the text did not mention it.

## 3. The inventory — one row per element, nothing dropped

```
Image 1 — Employees list (web), Active filter applied
- page: Employees > list                              relevant: yes
- filter: Status = Active                             relevant: yes — bounds the export
- columns (in order): Name, Job Title, Department, Start Date, Status   relevant: yes
- annotation: red box around the column headers       relevant: yes — marks the point
- row count: "showing 25 of 412"                      relevant: maybe — pagination vs all
- left nav items                                      relevant: no
```

Rules that keep the inventory honest:

- **Relevance is a decision, not a filter you apply silently.** Mark the irrelevant rows
  `no` rather than omitting them; that is the difference between "considered and dropped"
  and "never noticed".
- **Copy labels verbatim.** `Organization Type` stays `Organization Type` even where the
  surrounding prose is British English. Never normalise, translate or tidy a product
  label, a status name or an option value.
- **Describe, do not interpret.** "Status column shows Active for every visible row" is a
  row. "Only active employees are exported" is a conclusion, and it belongs to the calling
  skill after the gate.
- **Report what the image cannot tell you.** "Whether inactive employees appear further
  down the list is not visible" is worth a row — it is usually the question that matters.

## 4. Several images: one requirement, or several?

Most often several images are **one requirement seen from different angles** — different
sections, tabs, states, or parts of the same record. Decide from the requester's own
wording first, then from what the images share.

| Signal | Reading |
|---|---|
| "include all the information on the first and second screenshot" | One deliverable covering both |
| Same page, different tabs or sections | One requirement, several parts of the same surface |
| Same record shown before and after | One change, with current and desired behaviour |
| Same screen on web and on mobile | One requirement, two platforms — both platforms are in scope unless the requester said otherwise |
| Different pages, different asks in the text | Genuinely separate; say so, and let the caller decide whether that is one deliverable or several |
| Identical screenshots pasted twice | Duplicate, not two requirements — say so rather than inventing a difference |

State the relationship you concluded and the wording that decided it. A wrong
relationship is the most expensive image mistake available here: it turns one export into
two features, or two features into one under-specified export.

**Before/after pairs**: say explicitly which image is current behaviour and which is
desired, and how you know (the requester's wording, an annotation, a visible difference).
Guessing that round is how a working screen gets rebuilt.

## 5. Illegible, cropped, ambiguous or partly hidden

If it is not legible, it is not evidence. For each such region, judge one thing: **would
the unreadable part change the deliverable?**

- **Yes** → it becomes a question candidate. Hand it to the calling skill's gate with what
  you can see, what you cannot, and why it matters ("the third column header is cut off;
  it decides whether the export includes salary"). Ask for the specific missing thing — a
  fuller screenshot, or the value in words — not "please clarify".
- **No** → drop that detail and mark the row `no`. Do not guess it, and do not pad the
  deliverable with it.

A truncated list, a cut-off column, a scrollbar showing more content below, a collapsed
section, a tooltip covering a field: all of these mean *there is more you have not seen*.
Say so — the requirement may live in the part that was cropped out.

## 6. Never invent, never overstate

- Never claim an image shows something that cannot actually be read from it.
- Never invent an image, or refer to one that was not supplied.
- Never infer content beyond what is visible to fill a gap in the requirement — an
  off-screen field, a menu item behind a closed dropdown, a validation rule you did not
  see fire.
- Never assume the screenshot is current, or from the environment being changed, unless
  something in it says so (§2, environment hints).
- Where the image and the request text disagree — the text says "all suppliers", the
  screenshot shows a filter — report both as they are. Reconciling them is the gate's job,
  and this contradiction is nearly always the most important row you produce.

## 7. Boundaries — what this skill does not own

- **Tagging, coverage and the gate.** Evidence tags, dispositions, materiality, question
  rounds, the placeholder ban and the "requirement not sufficiently defined" report belong
  to the `requirement-evidence-and-gating` skill. This skill supplies image rows and
  question candidates; it does not decide whether the deliverable is written.
- **The deliverable.** Templates, sections, house style, where it is saved or created, and
  how images are attached to it belong to the calling skill (for example `ticket-writing`,
  which owns the Jira ticket template, its `Images` section and its attachment limits).
- **Verifying against code.** Confirming that what the image shows is what the code does
  is a `CODEBASE` claim, and the calling skill's job.
