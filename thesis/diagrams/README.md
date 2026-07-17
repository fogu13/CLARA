# Diagrams & Schemas

Editable source for every architecture / pipeline / flow / data-model figure in the thesis. **Format: Mermaid** (plain text) + **SQL** for the schema — chosen so you can edit them in tools you already use, with no proprietary file format and clean version control.

## Files

| File | What | Edit in |
|---|---|---|
| `01_architecture_logical.mmd` | Build-agnostic system architecture | any (below) |
| `../archive/odradek/02_architecture_odradek.mmd` | (retired) Odradek prototype — archived July 2026 | |
| `03_architecture_clara.mmd` | CLARA build (Next.js + FastAPI + LangGraph) | |
| `04_pipeline_flow.mmd` | Signal → Insight → Action → Learning, with governance gates | |
| `05_sequence_hitl.mmd` | Signal lifecycle sequence, human-in-the-loop | |
| `06_data_model_er.mmd` | Entity-relationship diagram | |
| `07_evaluation_pipeline.mmd` | Real-data gold-set evaluation harness | |
| `08_dsr_method.mmd` | Design Science method (Hevner cycles + DSRM) | |
| `schema.sql` | **Runnable** Postgres DDL for the data model | any SQL editor / psql |
| `diagrams.md` | All diagrams embedded in one Markdown file | Obsidian / GitHub |
| `rendered/*.png`, `*.svg` | Exported images (used in the Word build) | regenerated, don't hand-edit |

## How to edit

- **Obsidian** (you already use it): open `diagrams.md` — Mermaid renders live; edit the code block and it updates.
- **mermaid.live**: paste a `.mmd` file, edit visually-assisted, export PNG/SVG.
- **VS Code**: "Markdown Preview Mermaid Support" or "Mermaid Editor" extension.
- **draw.io / diagrams.net** (visual drag-and-drop): *Arrange → Insert → Advanced → Mermaid*, paste the `.mmd`. Gives you an editable visual canvas if you prefer not to touch text.
- **SQL**: edit `schema.sql` directly; run with `psql` or paste into the Supabase SQL editor.

## Re-render images (for the Word/PDF build)

```bash
python diagrams/render.py        # renders every .mmd → rendered/*.png + *.svg via mermaid.ink (needs internet)
```
No local install required. Offline, just edit/preview in Obsidian or mermaid.live; only re-run `render.py` when you want fresh images in `thesis.docx`.

## Gotchas when editing Mermaid

- Don't put a bare `&` inside a node label (it's a chaining operator) — write "and".
- Quote edge labels that contain `/` or `(` — e.g. `A -->|"a / b"| B`.
- Keep `<br/>` for line breaks inside labels.
