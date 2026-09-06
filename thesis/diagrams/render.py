"""Render every .mmd to PNG + SVG.

Usage:  python diagrams/render.py
The .mmd files are the editable source; this only refreshes diagrams/rendered/*.

Two renderers, tried in order:
  1. mermaid-cli (`mmdc`) if it is on PATH or named by MMDC — local, offline,
     deterministic; `npm install -g @mermaid-js/mermaid-cli`. Set
     PUPPETEER_CONFIG to a JSON file naming a Chromium executablePath when the
     bundled download is unavailable.
  2. mermaid.ink over HTTPS (no install), when no local renderer is available.
If neither works, edit/preview the .mmd in Obsidian, mermaid.live, or VS Code.
"""
import base64, glob, os, shutil, subprocess, sys, urllib.request

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


def render_local(mmdc, src, stem):
    """mermaid-cli: PNG at 1600px wide plus SVG, white background."""
    base = [mmdc, "-i", src, "-b", "white", "-q"]
    cfg = os.environ.get("PUPPETEER_CONFIG")
    if cfg:
        base += ["-p", cfg]
    subprocess.run(base + ["-o", os.path.join(OUT, stem + ".png"), "-w", "1600"], check=True)
    subprocess.run(base + ["-o", os.path.join(OUT, stem + ".svg")], check=True)
    return (os.path.getsize(os.path.join(OUT, stem + ".png")),
            os.path.getsize(os.path.join(OUT, stem + ".svg")))


def render_remote(code, stem):
    b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    png = fetch(f"https://mermaid.ink/img/{b64}?type=png&width=1600",
                os.path.join(OUT, stem + ".png"))
    svg = fetch(f"https://mermaid.ink/svg/{b64}", os.path.join(OUT, stem + ".svg"))
    return png, svg


def main():
    files = sorted(glob.glob(os.path.join(HERE, "*.mmd")))
    mmdc = os.environ.get("MMDC") or shutil.which("mmdc")
    print(f"renderer: {'mermaid-cli ' + mmdc if mmdc else 'mermaid.ink (remote)'}")
    ok = 0
    for f in files:
        code = open(f, encoding="utf-8").read()
        stem = os.path.splitext(os.path.basename(f))[0]
        try:
            png, svg = render_local(mmdc, f, stem) if mmdc else render_remote(code, stem)
            print(f"OK  {stem}: png {png}B, svg {svg}B")
            ok += 1
        except Exception as e:
            print(f"ERR {stem}: {e}")
    print(f"\n{ok}/{len(files)} rendered into {OUT}")
    sys.exit(0 if ok == len(files) else 1)


if __name__ == "__main__":
    main()
