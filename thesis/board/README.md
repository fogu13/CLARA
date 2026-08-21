# Thesis board

The thesis on one canvas, in four zones, for walking someone through the flows rather than
presenting slides at them. Built for the supervisor sessions and for the defense.

| Zone | What it answers |
|------|-----------------|
| 1. The governed loop, as it runs | How a signal becomes an approved action, a measured outcome, and a retrievable learning |
| 2. Governance, mapped onto the same loop | Which control governs which stage, EU AI Act article by article, with the bounds stated |
| 3. The evidence map | Every claim, its status, and the file that produced it, with the headline numbers |
| 4. The schema is the argument | Closure as referential integrity, memory as a column that decays |

## One spec, two renderers

`board_spec.json` is the single source of truth: zones, cards, edges, notes, coordinates and
colours. Two renderers read it, so the Miro board and the HTML canvas cannot drift apart.
Edit the spec, then re-run whichever renderers you use.

```
board_spec.json
├── miro_build.py    -> a real Miro board, via the REST API
└── build_canvas.py  -> canvas.html, a standalone pan-and-zoom page
```

Only the Python standard library is used. There is nothing to install.

## The HTML canvas

```
python3 thesis/board/build_canvas.py     # writes canvas.html
```

Open `canvas.html` in any browser, or publish it. Keys: `1`-`4` jump to a zone, `0` fits the
whole board, `+` and `-` zoom, arrows pan. Drag to pan, hold ctrl or cmd while scrolling to
zoom. Hovering a card traces what feeds it and dims everything else.

The page is self-contained apart from Google Fonts, works in light and dark, and carries a
screen-reader outline of each zone's flow order.

## The Miro board

Create a token once, about a minute:

1. <https://miro.com/app/settings/user-profile/apps>, create a developer team app
2. Give it `boards:read` and `boards:write`, then install it to your team
3. Copy the access token

The board built from this spec lives at <https://miro.com/app/board/uXjVHvrqOTY=/>.

```
python3 thesis/board/miro_build.py --board 'uXjVHvrqOTY='          # rebuild, prompts for token
python3 thesis/board/miro_build.py --board 'uXjVHvrqOTY=' --keep   # append instead of wiping
python3 thesis/board/miro_build.py                                 # a NEW, separate board
python3 thesis/board/miro_build.py --dry-run                       # plan only, no token needed
```

With no `MIRO_ACCESS_TOKEN` in the environment it prompts, and the input is hidden, which
keeps the token out of your shell history and out of the process list. If you do prefer an
env var, it has to be on the same line as the command: a shell invocation starts fresh, so an
`export` from a previous command is already gone. Quote the board id, it ends in `=`.

**A rebuild wipes the board first.** Anything added in Miro by hand, sticky notes, comments,
drawn arrows, is destroyed by a re-run. Once you start annotating the board with someone,
either stop re-running the script or keep the annotations on a frame outside the four zones
and use `--keep`, which appends instead of wiping.

About 100 items. If frame parenting misbehaves on your Miro plan, re-run with `--no-parent`
to place everything in absolute coordinates instead.

## Card anatomy

A card is a headline, an optional number, one sentence, and a caveat. Anything longer belongs
in the manuscript. The spec fields are:

| Field | Role |
|-------|------|
| `title` | two to four words |
| `metric` | the number, set large. Only where a number is the point |
| `lede` | one sentence, the thing to say out loud |
| `note` | the bound or caveat, set small under a rule |
| `step` | position in the loop. Draws a numbered badge, and only the loop is numbered |
| `table` | a real table in HTML, one labelled line per row in Miro |

Row heights are computed from this content, so a row is exactly as tall as its fullest card
and no taller. Lengthen a `lede` and the text will overflow its box in Miro, which uses fixed
boxes rather than min-heights. Miro cards are built with 12% height slack for that reason.

## Keeping it honest

Every number on the board is read from the repository, and the card that carries a number
names its source. When the evaluation changes, the numbers here have to change with it. The
cards most likely to go stale:

- zone 1, "Where this runs": endpoint count and deployment shape
- zone 3, all five result cards and the corpus card: `thesis/evaluation/results/summary.json`
- zone 3, "Held out": the three exploratory datasets, whose seed labels are still drafts
- zone 3, "What is still open": mirrors the traceability matrix in Appendix D

The board deliberately states bounds next to claims. Keep that. A card that gives a number
without its bound is the thing this thesis argues against.
