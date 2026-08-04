#!/usr/bin/env bash
# Render the spoken CLARA brief to audio using macOS built-in TTS.
#   ./make_audio.sh [voice] [words-per-minute]
# Voices: `say -v '?'`. Compact voices ship by default; Premium/Enhanced ones
# sound far better over 40 minutes and are a free download via
# System Settings > Accessibility > Spoken Content > System Voice > Manage Voices.
set -euo pipefail
cd "$(dirname "$0")"

VOICE="${1:-Daniel}"
RATE="${2:-170}"
SRC="clara-audio-brief.md"
OUT_DIR="build"
mkdir -p "$OUT_DIR"

# Strip the markdown front matter (everything above the --- rule) and any
# leftover markup, so the narrator never reads "hash" or "asterisk" aloud.
python3 - "$SRC" > "$OUT_DIR/clara-brief.txt" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
body = text.split("\n---\n", 1)[1] if "\n---\n" in text else text
body = re.sub(r"^#+ .*$", "", body, flags=re.M)     # headings
body = re.sub(r"[*_`]", "", body)                   # emphasis / code marks
body = re.sub(r"\n{3,}", "\n\n", body).strip()
print(body)
PY

WORDS=$(wc -w < "$OUT_DIR/clara-brief.txt" | tr -d ' ')
echo "script: $WORDS words -> ~$((WORDS / RATE)) min at $RATE wpm (voice: $VOICE)"

say -v "$VOICE" -r "$RATE" -o "$OUT_DIR/clara-brief.aiff" -f "$OUT_DIR/clara-brief.txt"

# m4a is ~10x smaller and plays anywhere; keep it if afconvert is present.
if command -v afconvert >/dev/null 2>&1; then
  afconvert -f m4af -d aac "$OUT_DIR/clara-brief.aiff" "$OUT_DIR/clara-brief.m4a"
  rm -f "$OUT_DIR/clara-brief.aiff"
  echo "wrote $OUT_DIR/clara-brief.m4a ($(du -h "$OUT_DIR/clara-brief.m4a" | cut -f1))"
else
  echo "wrote $OUT_DIR/clara-brief.aiff ($(du -h "$OUT_DIR/clara-brief.aiff" | cut -f1))"
fi
