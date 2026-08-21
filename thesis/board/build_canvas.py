#!/usr/bin/env python3
"""Render board_spec.json into a standalone pan-and-zoom HTML canvas.

Same spec as miro_build.py, so the Miro board and this canvas cannot drift.
Writes thesis/board/canvas.html, which is self-contained apart from Google Fonts.

Usage:
  python3 thesis/board/build_canvas.py
"""
from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "board_spec.json")
OUT = os.path.join(HERE, "canvas.html")

PAD = 700          # gutter around the whole plane
CORNER = 22        # wire corner radius
STUB = 70          # how far a wire steps out of a card before turning

# Card colours per kind, light then dark. The semantic hues keep their identity
# across themes; only lightness moves, so red still reads as a control point.
KINDS = {
    "llm":  (("#E4EDFD", "#3B6EA5", "#1B3552"), ("#17243F", "#5285C0", "#C3D7F7")),
    "det":  (("#FFFFFF", "#6B7488", "#1A1A2E"), ("#1B2138", "#778296", "#DFE4F2")),
    "gov":  (("#FDE4E4", "#C0392B", "#75201C"), ("#331A1A", "#C85C4E", "#F5CDC8")),
    "ext":  (("#EFF1F5", "#98A0AE", "#3D4453"), ("#1D2233", "#727C90", "#C7CEDE")),
    "data": (("#F3F6FD", "#2B3A78", "#22306E"), ("#171D33", "#7889CC", "#CAD3F2")),
    "fact": (("#FFFFFF", "#B9CDF2", "#1A1A2E"), ("#171C2F", "#3A456A", "#DFE4F2")),
    "good": (("#E6F3E8", "#2C5F2D", "#1C4520"), ("#16281A", "#548E56", "#C4E3C6")),
    "warn": (("#FDF2F2", "#9E0715", "#75201C"), ("#2C1518", "#B84A54", "#F2C8CC")),
    "navy": (("#1E2761", "#0E1440", "#FFFFFF"), ("#242E6B", "#5765B8", "#EEF1FF")),
}

# Type scale in plane units. Geometry sits at 1.7x the original grid and type at
# roughly 2.4x, which is what makes a card readable rather than a labelled box.
T_TITLE, T_METRIC, T_LEDE, T_NOTE, T_TABLE = 44, 92, 30, 24, 28
T_ZONE_H, T_ZONE_P, T_WIRE = 150, 62, 32


def e(s):
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
# wire routing
# --------------------------------------------------------------------------
def rect_of(node, zone):
    return {
        "x": zone["x"] + node["x"], "y": zone["y"] + node["y"],
        "w": node["w"], "h": node["h"],
        "cx": zone["x"] + node["x"] + node["w"] / 2,
        "cy": zone["y"] + node["y"] + node["h"] / 2,
    }


def side_point(r, side):
    return {
        "right":  (r["x"] + r["w"], r["cy"]),
        "left":   (r["x"], r["cy"]),
        "top":    (r["cx"], r["y"]),
        "bottom": (r["cx"], r["y"] + r["h"]),
    }[side]


def step_out(pt, side, d=STUB):
    x, y = pt
    return {"right": (x + d, y), "left": (x - d, y), "top": (x, y - d), "bottom": (x, y + d)}[side]


def infer_sides(a, b):
    if b["x"] >= a["x"] + a["w"] + 60:
        return "right", "left"
    if b["x"] + b["w"] + 60 <= a["x"]:
        return "left", "right"
    if b["y"] >= a["y"] + a["h"] + 60:
        return "bottom", "top"
    if b["y"] + b["h"] + 60 <= a["y"]:
        return "top", "bottom"
    return "right", "left"


def route(a, b, exit_side=None, enter_side=None):
    """Orthogonal two-elbow path from card a to card b, in plane coordinates."""
    if not exit_side or not enter_side:
        exit_side, enter_side = infer_sides(a, b)
    p0 = side_point(a, exit_side)
    p1 = step_out(p0, exit_side)
    p3 = side_point(b, enter_side)
    p2 = step_out(p3, enter_side)

    horiz = {"left", "right"}
    ex_h, en_h = exit_side in horiz, enter_side in horiz
    if ex_h and en_h:
        mx = (p1[0] + p2[0]) / 2
        mid = [(mx, p1[1]), (mx, p2[1])]
    elif not ex_h and not en_h:
        my = (p1[1] + p2[1]) / 2
        mid = [(p1[0], my), (p2[0], my)]
    elif ex_h and not en_h:
        mid = [(p2[0], p1[1])]
    else:
        mid = [(p1[0], p2[1])]

    pts, seen = [], None
    for p in [p0, p1, *mid, p2, p3]:
        p = (round(p[0], 1), round(p[1], 1))
        if p != seen:
            pts.append(p)
            seen = p
    return pts


def rounded_path(pts, r=CORNER):
    """Polyline to an SVG path with softened corners."""
    if len(pts) < 2:
        return ""
    d = [f"M {pts[0][0]} {pts[0][1]}"]
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        v1, v2 = (x1 - x0, y1 - y0), (x2 - x1, y2 - y1)
        l1 = max((v1[0] ** 2 + v1[1] ** 2) ** 0.5, 0.001)
        l2 = max((v2[0] ** 2 + v2[1] ** 2) ** 0.5, 0.001)
        rr = min(r, l1 / 2, l2 / 2)
        a = (x1 - v1[0] / l1 * rr, y1 - v1[1] / l1 * rr)
        c = (x1 + v2[0] / l2 * rr, y1 + v2[1] / l2 * rr)
        d.append(f"L {round(a[0],1)} {round(a[1],1)}")
        d.append(f"Q {x1} {y1} {round(c[0],1)} {round(c[1],1)}")
    d.append(f"L {pts[-1][0]} {pts[-1][1]}")
    return " ".join(d)


CHAR_W = 15.5   # rough advance for IBM Plex Sans at T_WIRE
LABEL_H = 44


def _clear(x, y, w, h, obstacles):
    left, right = x - w / 2 - 14, x + w / 2 + 14
    top, bottom = y - h / 2 - 8, y + h / 2 + 8
    for o in obstacles:
        if left < o["x"] + o["w"] and right > o["x"] and top < o["y"] + o["h"] and bottom > o["y"]:
            return False
    return True


def label_anchor(pts, text, obstacles):
    """Put the caption on open track. A label under a card is worse than none."""
    w, h = len(text) * CHAR_W, LABEL_H
    runs = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        runs.append((abs(x1 - x0) + abs(y1 - y0), (x0, y0), (x1, y1)))
    runs.sort(key=lambda r: -r[0])
    for length, (x0, y0), (x1, y1) in runs:
        if length < 70:
            continue
        vertical = abs(x1 - x0) < 1
        for t in (0.5, 0.35, 0.65):
            mx, my = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            slots = ([(mx, my), (mx + w / 2 + 34, my), (mx - w / 2 - 34, my)] if vertical
                     else [(mx, my - h / 2 - 10), (mx, my + h / 2 + 10), (mx, my - h / 2 - 64)])
            for sx, sy in slots:
                if _clear(sx, sy, w, h, obstacles):
                    return sx, sy
    return None


# --------------------------------------------------------------------------
# html
# --------------------------------------------------------------------------
def card_html(item, zone):
    NUM = " class=\"num\""
    x, y = zone["x"] + item["x"], zone["y"] + item["y"]
    p = [
        f'<article class="card k-{e(item["kind"])}" id="n-{e(item["id"])}" '
        f'data-node="{e(item["id"])}" tabindex="0" '
        f'style="left:{x}px;top:{y}px;width:{item["w"]}px;min-height:{item["h"]}px">'
    ]
    if item.get("step"):
        p.append(f'<span class="step" aria-hidden="true">{item["step"]}</span>')
    p.append(f'<h3>{e(item["title"])}</h3>')
    if item.get("metric"):
        p.append(f'<p class="metric">{e(item["metric"])}</p>')
    if item.get("lede"):
        p.append(f'<p class="lede">{e(item["lede"])}</p>')
    if item.get("table"):
        t = item["table"]
        p.append('<div class="tw"><table><thead><tr>')
        for i, head in enumerate(t["head"]):
            p.append("<th" + (NUM if i else "") + f">{e(head)}</th>")
        p.append("</tr></thead><tbody>")
        for row in t["rows"]:
            p.append("<tr>")
            for i, cell in enumerate(row):
                p.append("<td" + (NUM if i else "") + f">{e(cell)}</td>")
            p.append("</tr>")
        p.append("</tbody></table></div>")
    if item.get("note"):
        p.append(f'<p class="note">{e(item["note"])}</p>')
    p.append("</article>")
    return "".join(p)


def build():
    with open(SPEC, encoding="utf-8") as fh:
        spec = json.load(fh)

    zones = [{**z, "x": z["x"] + PAD, "y": z["y"] + PAD} for z in spec["zones"]]
    plane_w = max(z["x"] + z["w"] for z in zones) + PAD
    plane_h = max(z["y"] + z["h"] for z in zones) + PAD

    rects = {}
    for z in zones:
        for n in z["nodes"]:
            rects[n["id"]] = rect_of(n, z)

    obstacles = [{"x": z["x"] + i["x"], "y": z["y"] + i["y"], "w": i["w"], "h": i["h"]}
                 for z in zones for i in list(z["nodes"]) + list(z.get("notes", []))]

    wires, labels = [], []
    for z in zones:
        for edge in z.get("edges", []):
            a, b = rects.get(edge["from"]), rects.get(edge["to"])
            if not a or not b:
                continue
            pts = route(a, b, edge.get("exit"), edge.get("enter"))
            tone = edge.get("tone", "plain")
            wires.append(
                f'<path class="wire wire--{tone}" d="{rounded_path(pts)}" '
                f'marker-end="url(#tip-{tone})" data-from="{e(edge["from"])}" '
                f'data-to="{e(edge["to"])}" />'
            )
            if edge.get("label"):
                spot = label_anchor(pts, edge["label"], obstacles)
                if spot:
                    labels.append(
                        f'<text class="wire-label" x="{round(spot[0],1)}" y="{round(spot[1],1)+11}" '
                        f'text-anchor="middle" data-from="{e(edge["from"])}" data-to="{e(edge["to"])}">'
                        f'{e(edge["label"])}</text>'
                    )
                else:
                    print(f"  no clear slot for label {edge['label']!r}, dropped")

    frames, bands, cards, nav, outline = [], [], [], [], []
    for i, z in enumerate(zones, 1):
        frames.append(
            f'<section class="zone" id="{e(z["id"])}" '
            f'style="left:{z["x"]}px;top:{z["y"]}px;width:{z["w"]}px;height:{z["h"]}px">'
            f'<header class="zone-head"><h2>{e(z["title"])}</h2>'
            f'<p>{e(z["subtitle"])}</p></header></section>'
        )
        for band in z.get("bands", []):
            bands.append(
                f'<div class="band k-{e(band["kind"])}" style="left:{z["x"]+band["x"]}px;'
                f'top:{z["y"]+band["y"]}px;width:{band["w"]}px;height:{band["h"]}px">'
                f'<span>{e(band["label"])}</span></div>'
            )
        for n in list(z["nodes"]) + list(z.get("notes", [])):
            cards.append(card_html(n, z))
        nav.append(
            f'<button type="button" class="nav-zone" data-goto="{e(z["id"])}">'
            f'<span class="nav-n">{i}</span>{e(z.get("short") or z["title"])}</button>'
        )
        flow = " then ".join(n["title"] for n in z["nodes"])
        outline.append(
            f"<li><strong>{e(z['title'])}.</strong> {e(z['subtitle'])} Order: {e(flow)}.</li>"
        )

    legend = "".join(f'<li><span class="sw k-{e(k)}"></span>{e(label)}</li>'
                     for k, label in spec["legend"])

    def kind_block(dark):
        i = 1 if dark else 0
        return "\n".join(f"    --k-{k}-fill:{v[i][0]}; --k-{k}-line:{v[i][1]}; --k-{k}-ink:{v[i][2]};"
                         for k, v in KINDS.items())

    light = f"""
    --ground:#FAFBFE; --grid:#E2E9F7; --surface:#FFFFFF; --bar:#FFFFFFEE;
    --ink:#171B2E; --mute:#5A6478; --brand:#1E2761; --rule:#DCE4F4;
    --flow:#1E2761; --ret:#2C5F2D; --plain:#7A879F;
    --shadow:0 1px 2px rgba(23,27,46,.06),0 10px 26px rgba(23,27,46,.08);
{kind_block(False)}"""
    dark = f"""
    --ground:#0E1220; --grid:#1B2139; --surface:#161B2E; --bar:#111629EE;
    --ink:#E4E8F5; --mute:#97A1BC; --brand:#A8BCF5; --rule:#262E4A;
    --flow:#8FA3E8; --ret:#6FAE72; --plain:#5E6A85;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 12px 30px rgba(0,0,0,.4);
{kind_block(True)}"""

    meta = spec["meta"]
    return TEMPLATE.format(
        title=e(meta["title"]), author=e(meta["author"]), built=e(meta["built"]),
        note=e(meta["note"]), subtitle=e(meta["subtitle"]), light=light, dark=dark,
        plane_w=plane_w, plane_h=plane_h,
        wires="\n".join(wires), wire_labels="\n".join(labels),
        frames="\n".join(frames), bands="\n".join(bands), cards="\n".join(cards),
        nav="".join(nav), legend=legend, outline="".join(outline),
        t_title=T_TITLE, t_metric=T_METRIC, t_lede=T_LEDE, t_note=T_NOTE,
        t_table=T_TABLE, t_zone_h=T_ZONE_H, t_zone_p=T_ZONE_P, t_wire=T_WIRE,
    )


TEMPLATE = """<title>The Governed Loop</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap">
<style>
:root {{{light}
  --sans:"IBM Plex Sans",ui-sans-serif,system-ui,"Segoe UI",sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{{dark} }} }}
:root[data-theme="dark"] {{{dark} }}

* {{ box-sizing: border-box; }}
html, body {{ height: 100%; }}
body {{
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: var(--sans); -webkit-font-smoothing: antialiased; overflow: hidden;
}}
.sr {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0; }}

/* ---------- chrome ---------- */
.bar {{
  position: fixed; inset: 0 0 auto 0; z-index: 40; height: 58px;
  display: flex; align-items: center; gap: 14px; padding: 0 16px;
  background: var(--bar); backdrop-filter: blur(10px); border-bottom: 1px solid var(--rule);
}}
.brand {{ display: flex; align-items: baseline; gap: 10px; min-width: 0; }}
.brand h1 {{
  font-family: var(--serif); font-size: 17px; font-weight: 700; margin: 0;
  color: var(--brand); letter-spacing: -.01em; white-space: nowrap;
}}
.brand span {{ font-size: 12px; color: var(--mute); white-space: nowrap; }}
@media (max-width: 900px) {{ .brand span {{ display: none; }} }}
.nav {{ display: flex; gap: 6px; margin-left: auto; overflow-x: auto; scrollbar-width: none; }}
.nav::-webkit-scrollbar {{ display: none; }}
button {{ font: inherit; color: inherit; }}
.nav-zone, .tool {{
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  padding: 7px 11px; border-radius: 7px; border: 1px solid var(--rule);
  background: var(--surface); font-size: 12.5px; cursor: pointer;
  transition: border-color .15s, color .15s;
}}
.nav-zone:hover, .tool:hover {{ border-color: var(--brand); color: var(--brand); }}
.nav-zone[aria-current="true"] {{ border-color: var(--brand); color: var(--brand); font-weight: 600; }}
.nav-n {{
  font-family: var(--mono); font-size: 10.5px; width: 17px; height: 17px;
  display: grid; place-items: center; border-radius: 4px;
  background: var(--brand); color: var(--surface);
}}
.tools {{ display: flex; gap: 6px; }}
.tool {{ padding: 7px 10px; font-family: var(--mono); }}
:focus-visible {{ outline: 2px solid var(--brand); outline-offset: 3px; }}

/* ---------- canvas ---------- */
.stage {{
  position: fixed; inset: 58px 0 0 0; overflow: hidden; cursor: grab;
  background-color: var(--ground);
  background-image: radial-gradient(var(--grid) 1.5px, transparent 1.5px);
  background-size: 34px 34px; touch-action: none;
}}
.stage.dragging {{ cursor: grabbing; }}
.plane {{
  position: absolute; top: 0; left: 0; transform-origin: 0 0;
  transition: transform .42s cubic-bezier(.4, 0, .2, 1);
}}
.plane.instant {{ transition: none; }}

.zone {{
  position: absolute; border: 2px solid var(--rule); border-radius: 40px;
  background: color-mix(in srgb, var(--surface) 60%, transparent);
}}
.zone-head {{ padding: 90px 100px 0; }}
.zone-head h2 {{
  font-family: var(--serif); font-weight: 700; font-size: {t_zone_h}px; margin: 0 0 28px;
  color: var(--brand); letter-spacing: -.02em; line-height: 1.02; text-wrap: balance;
}}
.zone-head p {{ margin: 0; font-size: {t_zone_p}px; line-height: 1.35; color: var(--mute); max-width: 60ch; }}

.band {{
  position: absolute; border-radius: 30px;
  background: color-mix(in srgb, var(--line) 9%, transparent);
  border: 2px dashed color-mix(in srgb, var(--line) 34%, transparent);
}}
.band span {{
  position: absolute; left: 34px; bottom: -62px; font-size: 34px; font-weight: 600;
  letter-spacing: .05em; text-transform: uppercase;
  color: color-mix(in srgb, var(--line) 72%, transparent);
}}

.wires {{ position: absolute; top: 0; left: 0; overflow: visible; pointer-events: none; }}
.wire {{ fill: none; stroke-linejoin: round; stroke-linecap: round; transition: opacity .18s; }}
.wire--flow {{ stroke: var(--flow); stroke-width: 9; }}
.wire--plain {{ stroke: var(--plain); stroke-width: 6; }}
.wire--return {{ stroke: var(--ret); stroke-width: 7; stroke-dasharray: 26 20; }}
.tip-flow {{ fill: var(--flow); }}
.tip-plain {{ fill: var(--plain); }}
.tip-return {{ fill: var(--ret); }}
.wire-label {{
  font-family: var(--sans); font-size: {t_wire}px; font-weight: 500; fill: var(--mute);
  stroke: var(--ground); stroke-width: 10; paint-order: stroke fill;
  transition: fill .18s, opacity .18s;
}}

.card {{
  position: absolute; border-radius: 26px; padding: 30px 34px 32px;
  border: 3px solid var(--line); background: var(--fill); color: var(--fg);
  box-shadow: var(--shadow); transition: transform .16s, box-shadow .16s, opacity .18s;
}}
.card h3 {{ font-size: {t_title}px; font-weight: 600; margin: 0 0 16px; letter-spacing: -.015em; line-height: 1.15; }}
.card .metric {{
  font-family: var(--mono); font-size: {t_metric}px; font-weight: 600; line-height: 1;
  margin: 0 0 14px; letter-spacing: -.03em; font-variant-numeric: tabular-nums;
}}
.card .lede {{ font-size: {t_lede}px; line-height: 1.42; margin: 0 0 16px; }}
.card .note {{
  font-size: {t_note}px; line-height: 1.4; margin: 0; opacity: .74;
  border-top: 2px solid color-mix(in srgb, currentColor 20%, transparent); padding-top: 14px;
}}
.card > :last-child {{ margin-bottom: 0; }}
.card:hover, .card:focus-visible {{
  transform: translateY(-5px);
  box-shadow: 0 6px 12px rgba(23,27,46,.12), 0 28px 60px rgba(23,27,46,.16);
}}

.step {{
  position: absolute; top: -34px; left: -34px; width: 96px; height: 96px;
  border-radius: 50%; background: var(--line); color: var(--fill);
  display: grid; place-items: center; font-family: var(--mono);
  font-size: 46px; font-weight: 600; box-shadow: var(--shadow);
}}
.k-navy .step {{ color: #FFFFFF; }}

.tw {{ overflow-x: auto; margin: 0 0 18px; }}
/* color and font are set explicitly rather than inherited: with no doctype in the
   file, a browser opening canvas.html directly runs in quirks mode, where tables
   do not inherit either, and the result tables render dark on the navy cards. */
table {{
  border-collapse: collapse; width: 100%; color: inherit;
  font-family: var(--sans); font-size: {t_table}px; line-height: 1.35;
}}
th, td {{
  color: inherit; text-align: left; padding: 12px 22px 12px 0;
  border-bottom: 2px solid color-mix(in srgb, currentColor 22%, transparent);
}}
thead th {{ font-weight: 600; font-size: {t_note}px; text-transform: uppercase; letter-spacing: .06em; opacity: .72; }}
tbody tr:last-child td {{ border-bottom: 0; }}
.num {{ font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }}
thead .num {{ font-family: var(--sans); }}

.k-llm  {{ --fill: var(--k-llm-fill);  --line: var(--k-llm-line);  --fg: var(--k-llm-ink); }}
.k-det  {{ --fill: var(--k-det-fill);  --line: var(--k-det-line);  --fg: var(--k-det-ink); }}
.k-gov  {{ --fill: var(--k-gov-fill);  --line: var(--k-gov-line);  --fg: var(--k-gov-ink); }}
.k-ext  {{ --fill: var(--k-ext-fill);  --line: var(--k-ext-line);  --fg: var(--k-ext-ink); }}
.k-data {{ --fill: var(--k-data-fill); --line: var(--k-data-line); --fg: var(--k-data-ink); }}
.k-fact {{ --fill: var(--k-fact-fill); --line: var(--k-fact-line); --fg: var(--k-fact-ink); }}
.k-good {{ --fill: var(--k-good-fill); --line: var(--k-good-line); --fg: var(--k-good-ink); }}
.k-warn {{ --fill: var(--k-warn-fill); --line: var(--k-warn-line); --fg: var(--k-warn-ink); }}
.k-navy {{ --fill: var(--k-navy-fill); --line: var(--k-navy-line); --fg: var(--k-navy-ink); }}

.plane.tracing .card:not(.lit) {{ opacity: .28; }}
.plane.tracing .band {{ opacity: .3; }}
.plane.tracing .wire:not(.lit), .plane.tracing .wire-label:not(.lit) {{ opacity: .1; }}
.plane.tracing .wire.lit {{ stroke: var(--brand); stroke-width: 13; }}
.plane.tracing .wire-label.lit {{ fill: var(--brand); }}

/* ---------- legend ---------- */
.legend {{
  position: fixed; left: 14px; bottom: 14px; z-index: 30; max-width: 340px;
  background: var(--bar); backdrop-filter: blur(10px);
  border: 1px solid var(--rule); border-radius: 12px; padding: 12px 14px;
  font-size: 12px; box-shadow: var(--shadow);
}}
.legend summary {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--mute); font-weight: 600; cursor: pointer; list-style: none; }}
.legend summary::-webkit-details-marker {{ display: none; }}
.legend summary::after {{ content: " +"; font-family: var(--mono); }}
.legend[open] summary::after {{ content: " \\2212"; }}
.legend[open] summary {{ margin-bottom: 9px; }}
.legend ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
.legend li {{ display: flex; gap: 9px; align-items: flex-start; line-height: 1.4; }}
.sw {{ flex: 0 0 auto; width: 15px; height: 15px; border-radius: 4px; margin-top: 1px; background: var(--fill); border: 2px solid var(--line); }}
.legend footer {{ margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--rule); color: var(--mute); font-size: 11px; line-height: 1.45; }}
.legend kbd {{ font-family: var(--mono); font-size: 10.5px; border: 1px solid var(--rule); border-radius: 3px; padding: 0 4px; }}
@media (max-width: 720px) {{ .legend {{ display: none; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>

<header class="bar">
  <div class="brand"><h1>The Governed Loop</h1><span>{title}</span></div>
  <nav class="nav" aria-label="Zones">{nav}</nav>
  <div class="tools">
    <button type="button" class="tool" id="fit" title="Fit the whole board (0)">Fit</button>
    <button type="button" class="tool" id="zout" title="Zoom out (-)">&minus;</button>
    <button type="button" class="tool" id="zin" title="Zoom in (+)">+</button>
  </div>
</header>

<div class="sr">
  <h2>What this board shows</h2>
  <p>{subtitle} {note}</p>
  <ol>{outline}</ol>
</div>

<main class="stage" id="stage" role="application" aria-label="Pan and zoom board of the thesis. Drag to pan, hold control and scroll to zoom, press 1 to 4 to jump between zones.">
  <div class="plane" id="plane" style="width:{plane_w}px;height:{plane_h}px">
    {frames}
    {bands}
    <svg class="wires" width="{plane_w}" height="{plane_h}" viewBox="0 0 {plane_w} {plane_h}" aria-hidden="true">
      <defs>
        <marker id="tip-flow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path class="tip-flow" d="M 0 1 L 10 5 L 0 9 z" /></marker>
        <marker id="tip-plain" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path class="tip-plain" d="M 0 1 L 10 5 L 0 9 z" /></marker>
        <marker id="tip-return" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path class="tip-return" d="M 0 1 L 10 5 L 0 9 z" /></marker>
      </defs>
      {wires}
      {wire_labels}
    </svg>
    {cards}
  </div>
</main>

<details class="legend" id="legend" open>
  <summary>How to read it</summary>
  <ul>{legend}</ul>
  <footer><kbd>1</kbd>&ndash;<kbd>4</kbd> jump to a zone, <kbd>0</kbd> fit, <kbd>+</kbd> <kbd>&minus;</kbd> zoom, arrows pan. Hover a card to trace what feeds it.
  <br><br>{author} &middot; {built}. {note}</footer>
</details>

<script>
(function () {{
  var stage = document.getElementById('stage');
  var plane = document.getElementById('plane');
  var zones = Array.prototype.slice.call(document.querySelectorAll('.zone'));
  var navBtns = Array.prototype.slice.call(document.querySelectorAll('.nav-zone'));
  var MIN = 0.04, MAX = 1.6;
  var view = {{ x: 0, y: 0, k: 1 }}, current;

  // The camera is a CSS transition on the plane. A requestAnimationFrame loop
  // stalls half way when the tab loses focus; a transition always lands.
  function apply(instant) {{
    plane.classList.toggle('instant', !!instant);
    plane.style.transform = 'translate(' + view.x + 'px,' + view.y + 'px) scale(' + view.k + ')';
  }}
  function clampK(k) {{ return Math.min(MAX, Math.max(MIN, k)); }}
  function moveTo(to, instant) {{ view = {{ x: to.x, y: to.y, k: to.k }}; apply(instant); }}

  function frameOf(el, margin) {{
    var m = margin === undefined ? 140 : margin;
    var vw = stage.clientWidth, vh = stage.clientHeight;
    var k = clampK(Math.min(vw / (el.offsetWidth + m * 2), vh / (el.offsetHeight + m * 2)));
    return {{
      k: k,
      x: (vw - el.offsetWidth * k) / 2 - el.offsetLeft * k,
      y: (vh - el.offsetHeight * k) / 2 - el.offsetTop * k
    }};
  }}
  function goZone(el, now) {{
    moveTo(frameOf(el), now);
    current = el;
    navBtns.forEach(function (b) {{
      b.setAttribute('aria-current', b.dataset.goto === el.id ? 'true' : 'false');
    }});
  }}
  function fitAll(now) {{
    moveTo(frameOf(plane, 60), now);
    current = plane;
    navBtns.forEach(function (b) {{ b.setAttribute('aria-current', 'false'); }});
  }}
  function zoomBy(f, cx, cy) {{
    var px = cx === undefined ? stage.clientWidth / 2 : cx;
    var py = cy === undefined ? stage.clientHeight / 2 : cy;
    var k = clampK(view.k * f);
    view.x = px - (px - view.x) * (k / view.k);
    view.y = py - (py - view.y) * (k / view.k);
    view.k = k; apply(true);
  }}

  navBtns.forEach(function (b) {{
    b.addEventListener('click', function () {{ goZone(document.getElementById(b.dataset.goto)); }});
  }});
  document.getElementById('fit').addEventListener('click', function () {{ fitAll(); }});
  document.getElementById('zin').addEventListener('click', function () {{ zoomBy(1.3); }});
  document.getElementById('zout').addEventListener('click', function () {{ zoomBy(0.77); }});

  var drag = null;
  stage.addEventListener('pointerdown', function (ev) {{
    if (ev.target.closest('.card')) return;
    drag = {{ id: ev.pointerId, x: ev.clientX, y: ev.clientY, vx: view.x, vy: view.y }};
    stage.setPointerCapture(ev.pointerId);
    stage.classList.add('dragging');
  }});
  stage.addEventListener('pointermove', function (ev) {{
    if (!drag || ev.pointerId !== drag.id) return;
    view.x = drag.vx + (ev.clientX - drag.x);
    view.y = drag.vy + (ev.clientY - drag.y);
    apply(true);
  }});
  ['pointerup', 'pointercancel'].forEach(function (t) {{
    stage.addEventListener(t, function (ev) {{
      if (drag && ev.pointerId === drag.id) {{ drag = null; stage.classList.remove('dragging'); }}
    }});
  }});

  stage.addEventListener('wheel', function (ev) {{
    ev.preventDefault();
    if (ev.ctrlKey || ev.metaKey) {{
      var r = stage.getBoundingClientRect();
      zoomBy(Math.pow(0.995, ev.deltaY), ev.clientX - r.left, ev.clientY - r.top);
    }} else {{ view.x -= ev.deltaX; view.y -= ev.deltaY; apply(true); }}
  }}, {{ passive: false }});

  var wires = Array.prototype.slice.call(document.querySelectorAll('.wire, .wire-label'));
  function trace(id) {{
    if (!id) {{
      plane.classList.remove('tracing');
      wires.forEach(function (w) {{ w.classList.remove('lit'); }});
      document.querySelectorAll('.card.lit').forEach(function (c) {{ c.classList.remove('lit'); }});
      return;
    }}
    var touched = {{}}; touched[id] = true;
    wires.forEach(function (w) {{
      var hit = w.dataset.from === id || w.dataset.to === id;
      w.classList.toggle('lit', hit);
      if (hit) {{ touched[w.dataset.from] = true; touched[w.dataset.to] = true; }}
    }});
    document.querySelectorAll('.card').forEach(function (c) {{
      c.classList.toggle('lit', !!touched[c.dataset.node]);
    }});
    plane.classList.add('tracing');
  }}
  document.querySelectorAll('.card').forEach(function (c) {{
    c.addEventListener('pointerenter', function () {{ trace(c.dataset.node); }});
    c.addEventListener('pointerleave', function () {{ trace(null); }});
    c.addEventListener('focus', function () {{ trace(c.dataset.node); }});
    c.addEventListener('blur', function () {{ trace(null); }});
  }});

  document.addEventListener('keydown', function (ev) {{
    var t = ev.target;
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (t && t.closest && t.closest('input, textarea, [contenteditable]')) return;
    var k = ev.key;
    if (k >= '1' && k <= String(zones.length)) {{ goZone(zones[+k - 1]); ev.preventDefault(); }}
    else if (k === '0') {{ fitAll(); ev.preventDefault(); }}
    else if (k === '+' || k === '=') {{ zoomBy(1.3); ev.preventDefault(); }}
    else if (k === '-' || k === '_') {{ zoomBy(0.77); ev.preventDefault(); }}
    else if (k.indexOf('Arrow') === 0) {{
      var s = ev.shiftKey ? 700 : 240;
      if (k === 'ArrowLeft') view.x += s; else if (k === 'ArrowRight') view.x -= s;
      else if (k === 'ArrowUp') view.y += s; else view.y -= s;
      apply(true); ev.preventDefault();
    }}
  }});

  addEventListener('resize', function () {{
    if (!drag) goZone(current === plane ? zones[0] : current, true);
  }});
  goZone(zones[0], true);
  if (innerHeight < 700) document.getElementById('legend').removeAttribute('open');
}})();
</script>
"""


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build())
    print(f"wrote {os.path.relpath(OUT)}")
