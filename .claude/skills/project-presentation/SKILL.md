---
name: project-presentation
description: >
  Produces a manager-ready presentation about this codebase end to end: surveys
  the repo's docs, source, and (if present) ML training notebooks/scripts to
  write a context file explaining the architecture and key decisions, writes a
  companion gap file for anything not derivable from the repo (performance
  metrics, ops/business data), asks the requester the handful of things only
  they can decide (format, audience depth, how to frame known gaps), then
  builds one or more .pptx decks with python-pptx — a comprehensive detailed
  version, a short diagram-heavy version for a 5-10 minute talk, and/or an
  academic/technical-defense version (data → DB schema → architecture →
  algorithms → tracking → evaluation → architecture comparison → results →
  requirements → monitoring → conclusion) for a project defense or rigorous
  technical review. Use whenever the user asks to create/rebuild/update a
  presentation, deck, or slides "for my manager", "about this project",
  "about the architecture", "for my project defense", or similar —
  especially useful for redoing this from scratch later. Do NOT use for a
  quick text summary, a web/HTML artifact deck (use an Artifact instead), or
  single-slide requests where the two-phase process is overkill.
argument-hint: "[short|full|academic|both] [optional: specific focus or audience]"
license: MIT
---

# Project Presentation Builder

Two phases, run in order. Don't skip Phase 1 to jump to slides — the context
file is what keeps the deck accurate instead of generic, and it's reusable if
the deck needs to be redone or updated later.

## Phase 1 — Gather context

1. **Survey repo docs first**: README.md, AGENT.md/AGENTS.md/CLAUDE.md (root
   and per-subdir), DEV.md, ARCHITECTURE.md — whatever exists. These usually
   contain an explicit architecture diagram/table and a rationale section;
   don't re-derive what's already documented.
2. **Read the source for decisions docs don't cover.** Favor files that reveal
   *why*, not just *what*: config flags with comments, docstrings, code
   comments explaining a tradeoff, deploy/CI configs, auth/permission setup.
   Cross-check docs against code — docs go stale (e.g. a doc may say "mock
   auth" when the code has since wired up a real backend). Use the Explore
   agent for broad repo surveys; read files directly once you know which ones
   matter.
3. **If the repo trains an ML model**, read the training notebook/scripts
   fully, not just skimmed: data sourcing (where from, what license/rights),
   cleaning/labeling/class-mapping decisions and *why* they were made,
   augmentation strategy and what real-world conditions it simulates,
   train/val split strategy, hyperparameters and the reasoning behind
   non-default choices, evaluation approach, export/deployment packaging.
   Check whether referenced artifacts (trained weights, metrics files) exist
   in the repo — a training script that ships is not the same as a model that
   has actually been trained on real data; call that distinction out
   explicitly, it matters for the deck.
4. **Write two files under `presentation/`** in the repo (create the dir if
   missing):
   - `CONTEXT.md` — architecture overview, a "key decisions" section (one
     decision per subsection, each with a one-line rationale), the
     model-building narrative if applicable, and a suggested slide flow.
     This is source material for slides, not slide copy.
   - `DATA_NEEDED.md` — grouped placeholders for anything not derivable from
     the repo, e.g.:
     - **Model/ML metrics**: accuracy/precision/recall/mAP, benchmark
       numbers, training curves — anything the training code computes but
       whose output wasn't captured/committed.
     - **Application/ops metrics**: uptime, latency in production, cost,
       usage/user data, deployment environment specifics.
     - **Presentation-only decisions**: format, audience, template, whether
       to show known gaps prominently — decisions only the requester can
       make, not something to research.
5. **Ask before building anything**, using AskUserQuestion, only for what's
   genuinely undecided and belongs to the requester:
   - Target format (.pptx vs Markdown/artifact vs something else)
   - Deck length & audience technical depth (exec-brief vs technical manager
     vs wide circulation)
   - How any known gap/limitation you found (e.g. an unfinished/untrained
     component) should be framed: own it plainly as a slide, mention briefly
     and move on, or hold off until confirmed with the team.
   Record the answers back into `DATA_NEEDED.md`/`CONTEXT.md` (checked off)
   so a future re-run of this skill doesn't re-ask.

## Phase 2 — Build the deck(s)

### Setup
Check `python -c "import pptx"`; if missing, `pip install python-pptx`.

### Use the bundled toolkit — don't rebuild shape helpers from scratch
`pptx_toolkit.py` sits next to this SKILL.md. Copy it into the scratchpad
directory alongside your build script and `from pptx_toolkit import *`. It
already provides the brand palette (swap the RGBColor constants for the
target org's colors if given a template/brand), and helpers: `new_deck`,
`title_slide`, `section_slide`, `content_slide`, `add_rect`, `add_text`,
`add_box_label`, `add_arrow` (connectors with arrowheads), `flow_row` (an
auto-centered horizontal box-and-arrow diagram — the main tool for
"architecture diagram" and "data flow" slides), `add_table`, `add_bullets`,
`metric_placeholder_row` (a row of "TBD" metric cards), `callout_banner` (the
amber "placeholder / known gap" banner), and `validate_pptx`.

### CRITICAL — read this before writing any coordinate math
**Every x/y/w/h/cx/cy fed to a shape or connector must be an `int`, never a
`float`.** `Emu` is an int subclass, but Python 3's `/` always returns a
float even on int subclasses — `box_h / 2` silently produces a float, and if
that reaches slide XML as e.g. `x="2909163.5"`, **PowerPoint treats the file
as corrupt and shows a repair prompt on open.** This is not cosmetic; it's
invalid OOXML. Rules:
- Never write `something / 2` for a coordinate — use `half()` from the
  toolkit, or `// 2`.
- Prefer the toolkit's helpers (they wrap every coordinate in `Emu(int(...))`
  defensively) over calling `slide.shapes.add_shape(...)` /
  `add_connector(...)` directly.
- **After every `prs.save(path)`, call `validate_pptx(path)`** from the
  toolkit before telling the user the deck is ready. It reloads the file and
  greps every slide's raw XML for stray float coordinates — treat any
  non-zero match as a bug to fix, not something to explain away.

### Choosing what to build
Ask (or infer from the request) which variant(s) are wanted:

- **Full/detailed** (~20-25 slides): one slide per architectural decision
  with its rationale, the complete data/training narrative, tables for
  structured comparisons (architecture layers, dataset sources, hyperparameter
  tables), a metrics slide with real numbers or an explicit "pending" callout.
  Appropriate for a technical audience or as a reference document.
- **Short** (~10-12 slides, 5-10 minute talk): diagram-first using
  `flow_row` for architecture and data-flow — box-and-arrow, not bullet
  lists. One slide per major *decision* framed as a decision (e.g. "why this
  model architecture"), not an implementation deep-dive. Avoid naming
  specific frameworks/protocols (WebSockets, FastAPI, ONNX, etc.) unless the
  audience is implementation-level — describe capability, not tool. Use
  `metric_placeholder_row` + `callout_banner` for anything still pending.
  If something is built but not yet exercised on real data (e.g. a trained
  component with no real training run yet), don't just note the gap — sketch
  a concrete proposed path to close it (what data, what pipeline reuse, what
  validation step) as its own slide, especially when asked to keep momentum
  positive rather than lead with a weakness.
- **Academic / technical defense** (~25-35 slides): for a project defense,
  thesis committee, or rigorous technical review — not an exec/manager
  audience. Every section below must be represented as its own slide (or
  slide group); skipping one because the repo doesn't have the data is not
  an option — render it as a `callout_banner` "not yet measured" placeholder
  instead, listed explicitly in `DATA_NEEDED.md`, so the *shape* of the
  argument stays complete even where the *numbers* don't exist yet:
  1. **Project introduction** — the problem, the system objective, the
     end-to-end threat-detection pipeline at a glance.
  2. **Available data** — every dataset used (name/source), data types
     (video, still frames, bounding-box annotations, temporal/behavioral
     labels), preprocessing performed, and how behavioral classes (e.g.
     punching/stabbing/shooting) were organized, merged, or remapped across
     source taxonomies. Use `add_table` for a dataset-source comparison.
  3. **Database design** — which DB technology, the actual schema (draw it
     with `add_table`: table name, key columns, relationships), and how
     detections/tracking/inference logs/system events/performance metrics
     map onto it. Explain how the schema supports monitoring and analysis,
     not just storage.
  4. **System architecture** — the complete pipeline, video-in to
     threat-decision-out, as a `flow_row` diagram; a slide on how detection,
     tracking, temporal action recognition, and threat-decision logic hand
     off to each other.
  5. **Algorithms used** — one slide per major algorithm/model (detector,
     tracker, temporal classifier, decision logic), each stating *why that
     algorithm* was chosen over alternatives, not just what it does.
  6. **Tracking method** — how identity is maintained across frames, how
     tracking output feeds temporal/behavior recognition, with its own
     `flow_row` workflow diagram.
  7. **Performance evaluation** — explicitly split into frame-level detection
     metrics (precision/recall/F1/mAP) vs. temporal/behavior-recognition
     metrics, each metric's choice justified in one line. If the repo's own
     evaluation code/scripts have never been run against real data, say so
     plainly rather than presenting placeholder numbers as real.
  8. **Architecture comparison** — a table/chart contrasting architecture
     versions (e.g. before/after a specific change) and the measured effect
     on accuracy/robustness/efficiency. If no controlled before/after
     benchmark actually exists in the repo, don't fabricate one — state that
     comparison as a pending measurement (`callout_banner`), and describe
     *what changed* qualitatively while being explicit numbers aren't in yet.
  9. **Experimental results** — quantitative results, confusion matrices
     where available, best-performing configuration highlighted.
  10. **System requirements** — compute (CPU/GPU), video/frame-rate
      assumptions, latency expectations, deployment constraints.
  11. **Monitoring & administration** — the logging mechanism, the admin
      dashboard concept, real captured screenshots/metrics if any exist in
      the repo (prefer an embedded real screenshot over a redrawn mockup).
  12. **Key findings & conclusion** — what improved, current limitations,
      future work, in that order.
  Academic-defense tone differs from Short/Full: justify *why* each
  algorithm/metric/design choice was picked (defensible to a committee), not
  just describe it, and keep frame-level vs. temporal-level results visibly
  separate throughout rather than blending them into one metrics slide.
- If building both, keep the same palette/fonts across variants so they read
  as one family, and never overwrite a deck the user asked to keep — save
  under a distinguishing suffix (`_Short`, `_v2`) and confirm before
  replacing an existing file.

### Output
Save to `presentation/<ProjectName>_Presentation.pptx` and/or
`presentation/<ProjectName>_Presentation_Short.pptx`. Run `validate_pptx()`
on each before reporting completion.

## Re-running this skill later

- If `presentation/CONTEXT.md` already exists, read it first and ask whether
  to refresh it against current repo state or reuse it — don't redo all of
  Phase 1 if the codebase hasn't materially changed since it was written.
- Reuse `pptx_toolkit.py` as-is rather than re-deriving the shape helpers —
  it already encodes the float-EMU fix above.
