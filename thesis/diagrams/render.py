"""Render every .mmd to PNG + SVG via mermaid.ink (no local install needed).

Usage:  python diagrams/render.py
The .mmd files are the editable source; this only refreshes diagrams/rendered/*.
If offline, edit/preview the .mmd in Obsidian, mermaid.live, or VS Code instead.
"""
import base64, glob, os, sys, urllib.request

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "rendered")
os.makedirs(OUT, exist_ok=True)


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-diagrams"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    files = sorted(glob.glob(os.path.join(HERE, "*.mmd")))
    ok = 0
    for f in files:
        code = open(f, encoding="utf-8").read()
        b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
        stem = os.path.splitext(os.path.basename(f))[0]
        try:
            png = fetch(f"https://mermaid.ink/img/{b64}?type=png&width=1600",
                        os.path.join(OUT, stem + ".png"))
            svg = fetch(f"https://mermaid.ink/svg/{b64}", os.path.join(OUT, stem + ".svg"))
            print(f"OK  {stem}: png {png}B, svg {svg}B")
            ok += 1
        except Exception as e:
            print(f"ERR {stem}: {e}")
    print(f"\n{ok}/{len(files)} rendered into {OUT}")
    sys.exit(0 if ok == len(files) else 1)


if __name__ == "__main__":
    main()
