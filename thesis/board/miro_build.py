#!/usr/bin/env python3
"""Build the thesis board in Miro from board_spec.json.

The spec is the single source of truth. This script renders it into a real Miro
board (frames, shapes, connectors, titles); build_canvas.py renders the same spec
into a standalone HTML canvas. Edit the spec, re-run both, and they stay in step.

Setup, about a minute:
  1. Go to https://miro.com/app/settings/user-profile/apps, create a developer
     team app, give it boards:read and boards:write, and install it to your team.
  2. Copy the access token it shows you.
  3. export MIRO_ACCESS_TOKEN=...

The board built from this spec is uXjVHvrqOTY=, so a rebuild usually wants --board.
Running with no arguments creates a SECOND board rather than updating that one.

Run it with no token set and it prompts for one, which keeps the token out of
your shell history.

Usage:
  python3 thesis/board/miro_build.py --board uXjVHvrqOTY=   # prompts for the token
  python3 thesis/board/miro_build.py                  # create a NEW, separate board
  python3 thesis/board/miro_build.py --board <id>     # rebuild that board in place
  python3 thesis/board/miro_build.py --dry-run        # print the plan, call nothing
  python3 thesis/board/miro_build.py --no-parent      # if frame parenting misbehaves

Only the standard library is used, so there is nothing to install.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.miro.com/v2"
HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "board_spec.json")

# Miro renders text top-down inside a shape and does not shrink to fit, so the
# spec's box heights were chosen against this scale. Change both together.
# These match build_canvas.py, so the two renderings read the same at any zoom.
TITLE_PT, METRIC_PT, LEDE_PT, NOTE_PT, TABLE_PT = "44", "88", "30", "24", "28"
ZONE_TITLE_PT, ZONE_SUB_PT, STEP_PT = "150", "62", "46"
HEIGHT_SLACK = 1.12
WIRE = {"flow": ("#1E2761", "9", "normal"),
        "plain": ("#7A879F", "6", "normal"),
        "return": ("#2C5F2D", "7", "dashed")}


class MiroError(RuntimeError):
    pass


def _request(method: str, path: str, token: str, payload=None, retries: int = 5):
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 429:
                wait = float(e.headers.get("Retry-After") or (2 ** attempt))
                print(f"    rate limited, waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise MiroError(f"{method} {url} -> {e.code}\n{detail}") from None
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise MiroError(f"{method} {url} -> {e.reason}") from None
    raise MiroError(f"{method} {url} -> gave up after {retries} attempts")


def esc(text: str) -> str:
    """Miro accepts a small HTML subset. Escape, then honour paragraph breaks."""
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return out.replace("\n", "<br>")


def table_text(t) -> str:
    """Miro's HTML subset has no table, and padded columns collapse, so each row
    is written as one labelled line instead of a grid that would not survive."""
    head = t["head"]
    lines = [" / ".join(head[1:]) + ":"]
    for row in t["rows"]:
        lines.append(f'{row[0]}: ' + "  ".join(row[1:]))
    return "\n".join(lines)


def line(text: str, size: str, bold: bool = False) -> str:
    inner = f"<strong>{esc(text)}</strong>" if bold else esc(text)
    return f'<p><span style="font-size:{size}px">{inner}</span></p>'


def card_html(item) -> str:
    """A card is a headline, an optional number, one sentence, and a caveat.
    Anything longer belongs in the manuscript, not on a board."""
    parts = [line(item["title"], TITLE_PT, bold=True)]
    if item.get("metric"):
        parts.append(line(item["metric"], METRIC_PT, bold=True))
    if item.get("lede"):
        parts.append(line(item["lede"], LEDE_PT))
    if item.get("table"):
        parts.append(line(table_text(item["table"]), TABLE_PT, bold=True))
    if item.get("note"):
        parts.append(line(item["note"], NOTE_PT))
    return "".join(parts)


def centre(x, y, w, h):
    return x + w / 2.0, y + h / 2.0


class Builder:
    def __init__(self, spec, token, board_id=None, dry_run=False, parent=True):
        self.spec = spec
        self.token = token
        self.board_id = board_id
        self.dry_run = dry_run
        self.parent = parent
        self.ids: dict[str, str] = {}   # spec node id -> miro item id
        self.calls = 0
        self.failures: list[tuple[str, str]] = []

    # ---- plumbing -------------------------------------------------------
    def post(self, path, payload, critical=False):
        """One item. A single rejected item is recorded and skipped, so a payload
        the API dislikes cannot abandon the run half way through the board."""
        self.calls += 1
        if self.dry_run:
            return {"id": f"dry-{self.calls}"}
        try:
            result = _request("POST", path, self.token, payload)
        except MiroError as err:
            if critical:
                raise
            self.failures.append((path.rsplit("/", 1)[-1], str(err)))
            return {"id": None}
        time.sleep(0.12)  # stay well inside the credit-based rate limit
        return result

    def create_board(self):
        meta = self.spec["meta"]
        # No sharing policy is sent, so the board lands with your team's default,
        # which is private to you until you share it.
        board = self.post("/boards", {
            "name": f'{meta["title"]}. Thesis board',
            "description": meta["subtitle"],
        }, critical=True)
        self.board_id = board["id"]
        return board

    def wipe(self):
        """Remove every item so a rebuild lands on a clean board."""
        if self.dry_run:
            print("  [dry-run] would delete all existing items")
            return
        removed = 0
        cursor = None
        # Collect first, then delete: deleting while paginating skips items.
        doomed = []
        while True:
            q = "?limit=50" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
            page = _request("GET", f"/boards/{self.board_id}/items{q}", self.token)
            doomed += [it["id"] for it in page.get("data", [])]
            cursor = page.get("cursor")
            if not cursor:
                break
        for item_id in doomed:
            try:
                _request("DELETE", f"/boards/{self.board_id}/items/{item_id}", self.token)
                removed += 1
                time.sleep(0.1)
            except MiroError:
                pass  # children vanish with their frame; a 404 here is expected
        print(f"  cleared {removed} existing items")

    # ---- rendering ------------------------------------------------------
    def place(self, x, y, w, h, frame):
        """Absolute canvas top-left plus size -> the position payload Miro wants.

        Miro positions an item by its centre. For a parented item that centre is
        measured from the parent frame's TOP-LEFT, not from the frame centre;
        centre-relative values go negative and the API rejects them as
        "outside of parent boundaries".
        """
        cx, cy = centre(x, y, w, h)
        if frame and self.parent:
            fx, fy = frame["origin"]
            return {"x": cx - fx, "y": cy - fy}, {"id": frame["id"]}
        return {"x": cx, "y": cy}, None

    def shape(self, node, zone, frame):
        pal = self.spec["palette"][node["kind"]]
        x, y = zone["x"] + node["x"], zone["y"] + node["y"]
        pos, parent = self.place(x, y, node["w"], node["h"], frame)
        payload = {
            "data": {"content": card_html(node), "shape": "round_rectangle"},
            "style": {
                "fillColor": pal["fill"], "fillOpacity": "1",
                "borderColor": pal["border"], "borderWidth": "3", "borderOpacity": "1",
                "color": pal["text"], "fontFamily": "open_sans", "fontSize": LEDE_PT,
                "textAlign": "left", "textAlignVertical": "top",
            },
            "position": pos,
            # Miro shapes are a fixed box, not a min-height, and its typesetting
            # breaks lines differently from the browser. The row heights are sized
            # against the HTML metrics, so Miro gets a little slack; the tightest
            # vertical gap on the board still leaves ~200px.
            "geometry": {"width": node["w"], "height": round(node["h"] * HEIGHT_SLACK)},
        }
        if parent:
            payload["parent"] = parent
        item = self.post(f"/boards/{self.board_id}/shapes", payload)
        self.ids[node["id"]] = item["id"]
        return item

    def badge(self, node, zone, frame):
        """The numbered step, sitting on the card's top-left corner. The loop is a
        sequence, so the number carries real information rather than decoration."""
        pal = self.spec["palette"][node["kind"]]
        d = 96
        x = zone["x"] + node["x"] - d / 2
        y = zone["y"] + node["y"] - d / 2
        pos, parent = self.place(x, y, d, d, frame)
        payload = {
            "data": {"content": line(str(node["step"]), STEP_PT, bold=True), "shape": "circle"},
            "style": {
                "fillColor": pal["border"], "fillOpacity": "1",
                "borderColor": pal["border"], "borderWidth": "2",
                "color": "#FFFFFF", "fontFamily": "open_sans", "fontSize": STEP_PT,
                "textAlign": "center", "textAlignVertical": "middle",
            },
            "position": pos,
            "geometry": {"width": d, "height": d},
        }
        if parent:
            payload["parent"] = parent
        return self.post(f"/boards/{self.board_id}/shapes", payload)

    def band(self, band, zone, frame):
        """A soft container behind a row of cards, so the shape of the loop reads
        before any single card is read."""
        pal = self.spec["palette"][band["kind"]]
        x, y = zone["x"] + band["x"], zone["y"] + band["y"]
        pos, parent = self.place(x, y, band["w"], band["h"], frame)
        payload = {
            "data": {"content": "", "shape": "round_rectangle"},
            "style": {
                "fillColor": pal["fill"], "fillOpacity": "0.35",
                "borderColor": pal["border"], "borderWidth": "2", "borderOpacity": "0.45",
                "borderStyle": "dashed",
            },
            "position": pos,
            "geometry": {"width": band["w"], "height": band["h"]},
        }
        if parent:
            payload["parent"] = parent
        self.post(f"/boards/{self.board_id}/shapes", payload)
        # the band label sits just under it, in the gutter
        lpos, lparent = self.place(x + 34, y + band["h"] + 8, band["w"] - 68, 60, frame)
        lp = {
            "data": {"content": line(band["label"].upper(), "34", bold=True)},
            "style": {"color": pal["border"], "fontFamily": "open_sans",
                      "fontSize": "34", "textAlign": "left"},
            "position": lpos, "geometry": {"width": band["w"] - 68},
        }
        if lparent:
            lp["parent"] = lparent
        self.post(f"/boards/{self.board_id}/texts", lp)

    def text(self, content, x, y, w, size, colour, frame, bold=False):
        pos, parent = self.place(x, y, w, 80, frame)
        inner = f"<strong>{esc(content)}</strong>" if bold else esc(content)
        payload = {
            "data": {"content": f'<p>{inner}</p>'},
            "style": {"color": colour, "fontFamily": "open_sans", "fontSize": size, "textAlign": "left"},
            "position": pos,
            "geometry": {"width": w},
        }
        if parent:
            payload["parent"] = parent
        return self.post(f"/boards/{self.board_id}/texts", payload)

    def frame(self, zone):
        cx, cy = centre(zone["x"], zone["y"], zone["w"], zone["h"])
        item = self.post(f"/boards/{self.board_id}/frames", {
            "data": {"format": "custom", "title": zone["title"], "type": "freeform"},
            "style": {"fillColor": "#ffffff"},
            "position": {"x": cx, "y": cy},
            "geometry": {"width": zone["w"], "height": zone["h"]},
        })
        return {"id": item["id"], "centre": (cx, cy), "origin": (zone["x"], zone["y"])}

    def connector(self, edge):
        start, end = self.ids.get(edge["from"]), self.ids.get(edge["to"])
        if not start or not end:
            print(f"    skipping edge {edge['from']} -> {edge['to']}, item missing", file=sys.stderr)
            return
        colour, width, style = WIRE.get(edge.get("tone", "plain"), WIRE["plain"])
        payload = {
            "startItem": {"id": start},
            "endItem": {"id": end},
            "shape": "elbowed",
            "style": {
                "strokeColor": colour, "strokeWidth": width, "strokeStyle": style,
                "startStrokeCap": "none", "endStrokeCap": "arrow",
                "fontSize": "30", "textOrientation": "horizontal",
            },
        }
        if edge.get("label"):
            payload["captions"] = [{"content": esc(edge["label"]), "position": "50%"}]
        self.post(f"/boards/{self.board_id}/connectors", payload)

    def legend(self):
        """A key in the top-left gutter. The colour convention carries the argument."""
        x, y = 0, -420
        self.text(self.spec["meta"]["title"], x, y, 4000, "48", "#1E2761", None, bold=True)
        self.text(self.spec["meta"]["subtitle"], x, y + 110, 5200, "20", "#5A6478", None)
        self.text(self.spec["meta"]["note"], x, y + 180, 5200, "16", "#5A6478", None)
        for i, (kind, label) in enumerate(self.spec["legend"]):
            pal = self.spec["palette"][kind]
            cx, cy = centre(5600 + i * 1080, y, 300, 90)
            self.post(f"/boards/{self.board_id}/shapes", {
                "data": {"content": f'<p><span style="font-size:12px">{esc(label)}</span></p>',
                         "shape": "round_rectangle"},
                "style": {"fillColor": pal["fill"], "fillOpacity": "1", "borderColor": pal["border"],
                          "borderWidth": "2", "color": pal["text"], "fontFamily": "open_sans",
                          "fontSize": "12", "textAlign": "left", "textAlignVertical": "middle"},
                "position": {"x": cx + 240, "y": cy},
                "geometry": {"width": 1000, "height": 90},
            })

    def run(self):
        print(f"Building board from {os.path.relpath(SPEC)}")
        self.legend()
        for zone in self.spec["zones"]:
            print(f"  zone {zone['id']}: {zone['title']}")
            frame = self.frame(zone)
            # bands first: Miro stacks by creation order, so they stay behind the cards
            for band in zone.get("bands", []):
                self.band(band, zone, frame)
            self.text(zone["title"], zone["x"] + 100, zone["y"] + 90, zone["w"] - 200,
                      ZONE_TITLE_PT, "#1E2761", frame, bold=True)
            self.text(zone["subtitle"], zone["x"] + 100, zone["y"] + 290, zone["w"] - 200,
                      ZONE_SUB_PT, "#5A6478", frame)
            for node in zone["nodes"]:
                self.shape(node, zone, frame)
            for note in zone.get("notes", []):
                self.shape(note, zone, frame)
            for node in zone["nodes"]:
                if node.get("step"):
                    self.badge(node, zone, frame)
        for zone in self.spec["zones"]:
            for edge in zone.get("edges", []):
                self.connector(edge)
        return self.board_id


def main():
    ap = argparse.ArgumentParser(description="Build the thesis board in Miro.")
    ap.add_argument("--board", help="rebuild this board id in place instead of creating one")
    ap.add_argument("--dry-run", action="store_true", help="plan only, make no API calls")
    ap.add_argument("--no-parent", action="store_true",
                    help="place items in absolute coordinates instead of parenting them to frames")
    ap.add_argument("--keep", action="store_true", help="with --board, add to the board instead of wiping it")
    args = ap.parse_args()

    token = os.environ.get("MIRO_ACCESS_TOKEN", "").strip()
    if not token and not args.dry_run:
        # Prompt rather than demand an env var. A token pasted at a prompt stays out
        # of shell history and out of the process list, which a command-line one does not.
        if sys.stdin.isatty():
            try:
                token = getpass.getpass("Miro access token (input hidden): ").strip()
            except (EOFError, KeyboardInterrupt):
                sys.exit("\nCancelled.")
        if not token:
            sys.exit(
                "No Miro token.\n"
                "Either paste one at the prompt, or set it on the SAME line as the command,\n"
                "because each shell invocation starts fresh and an earlier export is gone:\n\n"
                "  MIRO_ACCESS_TOKEN=paste_the_real_token python3 thesis/board/miro_build.py --board <id>\n\n"
                "Token setup is in the notes at the top of this file."
            )

    with open(SPEC, encoding="utf-8") as fh:
        spec = json.load(fh)

    b = Builder(spec, token, board_id=args.board, dry_run=args.dry_run, parent=not args.no_parent)
    if args.board:
        if not args.keep:
            print(f"Rebuilding board {args.board}")
            b.wipe()
    else:
        board = b.create_board()
        print(f"Created board {b.board_id}")
        if not args.dry_run:
            print(f"  {board.get('viewLink', '')}")

    board_id = b.run()
    print(f"\nDone. {b.calls} items, {len(b.failures)} rejected.")
    if b.failures:
        print("\nRejected items (the rest of the board is fine):")
        for kind, err in b.failures[:5]:
            print(f"  {kind}: {err.splitlines()[0]}")
        if len(b.failures) > 5:
            print(f"  ... and {len(b.failures) - 5} more of the same kinds")
    if not args.dry_run:
        print(f"\nOpen: https://miro.com/app/board/{board_id}/")


if __name__ == "__main__":
    main()
