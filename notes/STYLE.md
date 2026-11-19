# How renderobjects.com teaches (and how this site copies the method)

Notes from reading every page of renderobjects.com (20 guides, 16 API docs,
3 examples). This is the house style for every page on this site.

## Why the model site is easy to learn from

1. **Three doors, three needs.** Guides = understand (what, why, how).
   API = recall (the contract of one method plus typical implementations).
   Examples = ground it (real code, decisions explained). Each index page is
   two sentences and two cross-links to the other doors.
2. **One topic per page, scope stated out loud.** "We'll skip painting, hit
   testing, and compositing entirely — this is about layout, and only layout."
3. **A fixed skeleton**, so the reader always knows where they are (below).
4. **Every section opens with a one-sentence plain definition.**
   "Parent data is the per-child storage that the parent owns…"
5. **It says what you can ignore.** "Most layouts don't need this."
   "When You Don't Need to Override." "What You Get For Free."
6. **Why before how, and the symptom of every mistake.** "Forgetting this is
   the single most common bug… the property changes, but the screen doesn't
   update."
7. **Concrete numbers.** "If offset happens to be (100, 200)… the rectangle
   ends up at (150, 250)."
8. **Tiny snippets** (3–15 lines), only the relevant lines, comments inside
   the code carry the explanation. Long code only in Examples.
9. **Guides are text + code only.** No screenshots. Live demos only in
   Examples. (This site allows at most one simple diagram per guide, because
   scrolling is spatial.)
10. **Calm UI.** Dark, one accent blue, three columns (sidebar / content /
    "On this page"), mono uppercase group labels, nothing else.

## Guide skeleton

- Header: `Title` + one-line description.
- Intro paragraph: "This guide walks experienced Flutter developers through
  X. By the end, you'll understand Y. We'll skip A, B, and C — this is about
  X, and only X."
- `## What This Guide Covers` — bullets: **Section Name** — one sentence.
- `## The <thing> …` — where it lives in code. "You do three things, in this
  order: 1. 2. 3. That's the whole job. The rest of the guide unpacks each
  piece."
- One `##` per concept. First sentence defines it. Then how, a snippet, the
  rule in **bold**, the consequence of breaking it.
- Optional `> **Aside:** …` blockquote (rare: about 1 per guide at most).
- End with `## Common Pitfalls` (bold lead sentence per pitfall, as
  paragraphs) or `## Performance Notes` ("A few things to keep in mind:" +
  bullets with bold lead sentences).
- Last paragraph: "That's X end to end. …" one-paragraph recap.
- Conceptual survey guides end with `## Mental Model Summary` bullets.

Recurring section names worth reusing: "What X Actually Is", "The Pieces
Involved", "How the Pieces Connect", "What You Get For Free", "When You
Don't Need to …", "When You Do Need to …", "Common Pitfalls".

## API page skeleton

- Header: `methodName()` + "Implement/Use the methodName() method …".
- 1–2 sentences: what it is responsible for (or a 2-bullet list).
- `## Default Implementation` first (or "There Is None").
- Then recipe sections named by scenario: "No Children - Take Up All Space",
  "One Child - Same Size As Child". One or two sentences, then code.
- No pitfalls section, no recap. It is a cookbook.

## Example page skeleton

- Header: name + "Custom … that …".
- 1–2 sentences on what it is.
- `## Why …?` / `## The Goal` — why this needs custom code.
- `## Try it Out` — the live demo.
- `## The Implementation` with `###` per responsibility; each is 1–2 short
  paragraphs + the real code.
- `## Full Source Code`, `## Similar Implementations` (bullets).

## Voice

- Second person, present tense: "you", "your physics", "the framework".
- Short declarative sentences. Em dashes for asides. No exclamation marks,
  no emoji, no hype words.
- Rhetorical question to open a "why" section is fine: "If widgets describe
  the UI and render objects do the work, what is the element tree for?"
- Signposts: "A subtle point:", "The catch is…", "The practical takeaway:",
  "A few gotchas worth knowing:", "In short:".
- Bold only for the one rule that matters in a paragraph and for lead-ins.
- Inline code for every identifier. Method names without parens in prose
  headings ("The `performLayout` Method"), with parens in API titles.
- Never state something the source does not do. Every claim on this site is
  checked against the Flutter source in the local checkout.

## What "not overwhelming" means here

- Fewer pages than the model, each one focused; a single reading order.
- Introduce at most one new class per section.
- Prefer the common path; push rare cases into one "Going Further" group.
- Field-by-field reference lives in API pages, not in guides.
